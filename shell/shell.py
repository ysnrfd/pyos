"""
PyOS Shell Module

The interactive command-line shell for PyOS.

Author: YSNRFD
Version: 1.0.0
"""

import threading
import time
from typing import Optional, Any

from .parser import CommandParser, ParsedCommand
from .builtins import BuiltinCommands
from pyos.core.config_loader import get_config
from pyos.logger import Logger, get_logger


class Shell:
    """
    PyOS Interactive Shell.
    
    Provides:
    - Command parsing
    - Built-in commands
    - Pipeline execution
    - I/O redirection
    - Background execution
    - Command history
    - Environment variables
    
    Example:
        >>> shell = Shell(kernel)
        >>> shell.run()
    """
    
    def __init__(self, kernel=None):
        self._kernel = kernel
        self._logger = get_logger('shell')
        self._parser = CommandParser()
        self._builtins = BuiltinCommands(self)
        self._running = False
        self._exiting = False
        
        # Current session state
        self._cwd = '/'
        self._uid = 0
        self._gid = 0
        self._user = 'root'
        self._session = None
        self._environ: dict[str, str] = {
            'PATH': '/bin:/usr/bin',
            'HOME': '/root',
            'USER': 'root',
            'SHELL': '/bin/pysh',
            'TERM': 'xterm',
        }
        
        # Prompt
        self._prompt = '$ '
    
    @property
    def kernel(self):
        return self._kernel
    
    @property
    def cwd(self) -> str:
        return self._cwd
    
    @cwd.setter
    def cwd(self, value: str):
        self._cwd = value
        self._environ['PWD'] = value
    
    @property
    def current_uid(self) -> int:
        return self._uid
    
    @current_uid.setter
    def current_uid(self, value: int):
        self._uid = value
    
    @property
    def current_gid(self) -> int:
        return self._gid
    
    @current_gid.setter
    def current_gid(self, value: int):
        self._gid = value
    
    @property
    def current_user(self) -> str:
        return self._user
    
    @current_user.setter
    def current_user(self, value: str):
        self._user = value
        self._environ['USER'] = value
    
    @property
    def current_session(self):
        return self._session
    
    @current_session.setter
    def current_session(self, value):
        self._session = value
    
    @property
    def environ(self) -> dict[str, str]:
        return self._environ
    
    @property
    def parser(self) -> CommandParser:
        return self._parser
    
    def run(self) -> None:
        """
        Run the interactive shell.
        
        This is the main REPL loop.
        """
        self._running = True
        
        config = get_config()
        
        # Welcome message
        print(f"\n{config.kernel.boot_message}")
        print(f"Type 'help' for a list of commands.\n")
        
        while self._running and not self._exiting:
            try:
                # Get prompt
                prompt = self._get_prompt()
                
                # Read command
                try:
                    line = input(prompt)
                except EOFError:
                    print()
                    break
                except KeyboardInterrupt:
                    print("^C")
                    continue
                
                # Parse and execute
                self._execute_line(line)
                
            except Exception as e:
                self._logger.error(f"Shell error: {e}")
                print(f"shell: error: {e}")
        
        self._running = False
    
    def _get_prompt(self) -> str:
        """Generate the shell prompt."""
        config = get_config()
        
        # Show username and cwd
        if self._uid == 0:
            prompt_char = '#'
        else:
            prompt_char = '$'
        
        # Show shortened path
        if self._cwd == '/':
            cwd_display = '/'
        elif self._cwd.startswith('/home/'):
            parts = self._cwd.split('/')
            if len(parts) >= 3:
                cwd_display = f"~/{'/'.join(parts[3:])}"
            else:
                cwd_display = '~'
        else:
            cwd_display = self._cwd
        
        return f"{self._user}@pyos:{cwd_display}{prompt_char} "
    
    def _execute_line(self, line: str) -> int:
        """
        Execute a command line.
        
        Args:
            line: Command line string
        
        Returns:
            Exit code
        """
        # Parse the line
        cmd = self._parser.parse(line)
        
        if cmd is None:
            return 0
        
        # Execute command(s)
        return self._execute_command(cmd)
    
    def _execute_command(self, cmd: ParsedCommand, stdin_data: bytes = b'') -> int:
        """
        Execute a parsed command.
        
        Args:
            cmd: Parsed command
            stdin_data: Data from pipe stdin
        
        Returns:
            Exit code
        """
        if not cmd.command:
            return 0
        
        # Check for pipe
        if cmd.pipe_to:
            return self._execute_pipeline(cmd)
        
        # Check for built-in
        if self._builtins.is_builtin(cmd.command):
            return self._execute_builtin(cmd)
        
        # Execute as external command (simulated)
        return self._execute_external(cmd, stdin_data)
    
    def _execute_builtin(self, cmd: ParsedCommand) -> int:
        """Execute a built-in command."""
        return self._builtins.execute(cmd.command, cmd.args)
    
    def _execute_external(
        self,
        cmd: ParsedCommand,
        stdin_data: bytes = b''
    ) -> int:
        """Execute an external command (simulated)."""
        # For now, we simulate external commands
        # In a real OS, this would fork/exec a new process
        
        print(f"{cmd.command}: command not found")
        return 127
    
    def _execute_pipeline(self, cmd: ParsedCommand) -> int:
        """Execute a pipeline of commands."""
        commands = []
        current = cmd
        
        # Collect all commands in pipeline
        while current:
            commands.append(current)
            current = current.pipe_to
        
        # Execute each command, passing output to next
        data = b''
        exit_code = 0
        
        for i, c in enumerate(commands):
            # Store redirections
            redirs = c.redirections
            
            # Execute command
            if self._builtins.is_builtin(c.command):
                # Capture output for builtins
                import io
                import sys
                
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()
                
                exit_code = self._builtins.execute(c.command, c.args)
                
                output = sys.stdout.getvalue()
                sys.stdout = old_stdout
                
                data = output.encode()
            else:
                exit_code = self._execute_external(c, data)
            
            # Apply redirections (last command only for now)
            if i == len(commands) - 1:
                for redir in redirs:
                    if redir.type in ('out', 'append'):
                        self._write_file(redir.path, data, append=(redir.type == 'append'))
        
        return exit_code
    
    def _write_file(self, path: str, data: bytes, append: bool = False) -> bool:
        """Write data to a file."""
        if not self._kernel or not self._kernel.filesystem:
            return False
        
        try:
            from pyos.filesystem.vfs import OpenMode
            
            mode = OpenMode.APPEND if append else OpenMode.WRITE
            fd = self._kernel.filesystem.open(
                path, mode,
                uid=self._uid, gid=self._gid, cwd=self._cwd
            )
            
            self._kernel.filesystem.write(fd, data)
            self._kernel.filesystem.close(fd)
            
            return True
        except Exception as e:
            print(f"error writing {path}: {e}")
            return False
    
    def request_exit(self) -> None:
        """Request the shell to exit."""
        self._exiting = True
    
    def stop(self) -> None:
        """Stop the shell."""
        self._running = False
    
    def run_script(self, script: str) -> int:
        """
        Run a script (multiple commands).
        
        Args:
            script: Script content
        
        Returns:
            Last exit code
        """
        exit_code = 0
        
        for line in script.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                exit_code = self._execute_line(line)
        
        return exit_code
    
    def get_variable(self, name: str) -> Optional[str]:
        """Get an environment variable."""
        return self._environ.get(name)
    
    def set_variable(self, name: str, value: str) -> None:
        """Set an environment variable."""
        self._environ[name] = value
    
    def expand_variables(self, text: str) -> str:
        """Expand environment variables in text."""
        import re
        
        def replace_var(match):
            name = match.group(1) or match.group(2)
            return self._environ.get(name, '')
        
        # Match $VAR or ${VAR}
        return re.sub(r'\$(\w+|\{(\w+)\})', replace_var, text)


def create_shell(kernel=None) -> Shell:
    """Factory function to create a shell."""
    return Shell(kernel)
