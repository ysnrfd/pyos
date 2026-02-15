"""
Command Parser Module

Parses shell commands into structured format.

Author: YSNRFD
Version: 1.0.0
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class TokenType(Enum):
    """Token types for command parsing."""
    WORD = "word"
    PIPE = "pipe"
    REDIRECT_OUT = "redirect_out"
    REDIRECT_APPEND = "redirect_append"
    REDIRECT_IN = "redirect_in"
    BACKGROUND = "background"
    SEMICOLON = "semicolon"
    QUOTE = "quote"
    ESCAPE = "escape"


@dataclass
class Token:
    """A parsed token."""
    type: TokenType
    value: str


@dataclass
class Redirection:
    """A file redirection."""
    type: str  # "out", "append", "in"
    path: str


@dataclass
class ParsedCommand:
    """A parsed command line."""
    command: str
    args: List[str] = field(default_factory=list)
    redirections: List[Redirection] = field(default_factory=list)
    background: bool = False
    pipe_to: Optional['ParsedCommand'] = None


class CommandParser:
    """
    Parses shell command lines.
    
    Handles:
    - Command and arguments
    - Pipes (|)
    - Redirections (>, >>, <)
    - Background execution (&)
    - Quoted strings
    - Escape sequences
    
    Example:
        >>> parser = CommandParser()
        >>> cmd = parser.parse("ls -la | grep test > output.txt")
    """
    
    def __init__(self):
        self._history: List[str] = []
    
    def parse(self, line: str) -> Optional[ParsedCommand]:
        """
        Parse a command line.
        
        Args:
            line: Command line string
        
        Returns:
            ParsedCommand or None if empty
        """
        line = line.strip()
        
        if not line or line.startswith('#'):
            return None
        
        # Add to history
        self._history.append(line)
        
        # Tokenize
        tokens = self._tokenize(line)
        
        if not tokens:
            return None
        
        # Parse into command structure
        return self._parse_tokens(tokens)
    
    def _tokenize(self, line: str) -> List[Token]:
        """Convert a line into tokens."""
        tokens = []
        current = ""
        in_quote = None
        i = 0
        
        while i < len(line):
            char = line[i]
            
            # Handle quotes
            if char in ('"', "'") and in_quote is None:
                in_quote = char
                i += 1
                continue
            
            if char == in_quote:
                in_quote = None
                i += 1
                continue
            
            # Handle escape
            if char == '\\' and i + 1 < len(line):
                current += line[i + 1]
                i += 2
                continue
            
            # Inside quotes, just add character
            if in_quote:
                current += char
                i += 1
                continue
            
            # Handle special characters
            if char == '|':
                if current:
                    tokens.append(Token(TokenType.WORD, current))
                    current = ""
                tokens.append(Token(TokenType.PIPE, '|'))
                i += 1
                continue
            
            if char == '>':
                if current:
                    tokens.append(Token(TokenType.WORD, current))
                    current = ""
                
                if i + 1 < len(line) and line[i + 1] == '>':
                    tokens.append(Token(TokenType.REDIRECT_APPEND, '>>'))
                    i += 2
                else:
                    tokens.append(Token(TokenType.REDIRECT_OUT, '>'))
                    i += 1
                continue
            
            if char == '<':
                if current:
                    tokens.append(Token(TokenType.WORD, current))
                    current = ""
                tokens.append(Token(TokenType.REDIRECT_IN, '<'))
                i += 1
                continue
            
            if char == '&':
                if current:
                    tokens.append(Token(TokenType.WORD, current))
                    current = ""
                tokens.append(Token(TokenType.BACKGROUND, '&'))
                i += 1
                continue
            
            if char == ';':
                if current:
                    tokens.append(Token(TokenType.WORD, current))
                    current = ""
                tokens.append(Token(TokenType.SEMICOLON, ';'))
                i += 1
                continue
            
            # Handle whitespace
            if char.isspace():
                if current:
                    tokens.append(Token(TokenType.WORD, current))
                    current = ""
                i += 1
                continue
            
            # Regular character
            current += char
            i += 1
        
        # Don't forget last token
        if current:
            tokens.append(Token(TokenType.WORD, current))
        
        return tokens
    
    def _parse_tokens(self, tokens: List[Token]) -> ParsedCommand:
        """Parse tokens into a command structure."""
        cmd = ParsedCommand(command="")
        current_cmd = cmd
        current_tokens = []
        
        for i, token in enumerate(tokens):
            if token.type == TokenType.WORD:
                current_tokens.append(token.value)
            
            elif token.type == TokenType.PIPE:
                # Create next command and link
                self._apply_tokens(current_cmd, current_tokens)
                current_tokens = []
                
                next_cmd = ParsedCommand(command="")
                current_cmd.pipe_to = next_cmd
                current_cmd = next_cmd
            
            elif token.type == TokenType.REDIRECT_OUT:
                # Get next token as path
                if i + 1 < len(tokens) and tokens[i + 1].type == TokenType.WORD:
                    current_cmd.redirections.append(
                        Redirection(type="out", path=tokens[i + 1].value)
                    )
            
            elif token.type == TokenType.REDIRECT_APPEND:
                if i + 1 < len(tokens) and tokens[i + 1].type == TokenType.WORD:
                    current_cmd.redirections.append(
                        Redirection(type="append", path=tokens[i + 1].value)
                    )
            
            elif token.type == TokenType.REDIRECT_IN:
                if i + 1 < len(tokens) and tokens[i + 1].type == TokenType.WORD:
                    current_cmd.redirections.append(
                        Redirection(type="in", path=tokens[i + 1].value)
                    )
            
            elif token.type == TokenType.BACKGROUND:
                current_cmd.background = True
        
        # Apply remaining tokens
        self._apply_tokens(current_cmd, current_tokens)
        
        return cmd
    
    def _apply_tokens(
        self,
        cmd: ParsedCommand,
        tokens: List[str]
    ) -> None:
        """Apply tokens to a command."""
        if tokens:
            cmd.command = tokens[0]
            cmd.args = tokens[1:]
    
    def get_history(self) -> List[str]:
        """Get command history."""
        return self._history
    
    def clear_history(self) -> None:
        """Clear command history."""
        self._history.clear()
