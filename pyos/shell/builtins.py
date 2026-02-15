"""
Shell Built-in Commands

Implements built-in shell commands.

Author: YSNRFD
Version: 1.0.0
"""

from typing import Optional, Any, Callable, List
import time


class BuiltinCommands:
    """
    Built-in shell commands.
    
    These commands are executed directly by the shell without
    creating a new process.
    """
    
    def __init__(self, shell):
        """
        Initialize built-in commands.
        
        Args:
            shell: The shell instance
        """
        self._shell = shell
        self._commands: dict[str, Callable] = {
            'help': self.cmd_help,
            'exit': self.cmd_exit,
            'quit': self.cmd_exit,
            'ls': self.cmd_ls,
            'cd': self.cmd_cd,
            'pwd': self.cmd_pwd,
            'mkdir': self.cmd_mkdir,
            'rmdir': self.cmd_rmdir,
            'touch': self.cmd_touch,
            'rm': self.cmd_rm,
            'cat': self.cmd_cat,
            'echo': self.cmd_echo,
            'ps': self.cmd_ps,
            'kill': self.cmd_kill,
            'chmod': self.cmd_chmod,
            'chown': self.cmd_chown,
            'whoami': self.cmd_whoami,
            'id': self.cmd_id,
            'uname': self.cmd_uname,
            'clear': self.cmd_clear,
            'history': self.cmd_history,
            'export': self.cmd_export,
            'env': self.cmd_env,
            'date': self.cmd_date,
            'uptime': self.cmd_uptime,
            'free': self.cmd_free,
            'df': self.cmd_df,
            'mount': self.cmd_mount,
            'umount': self.cmd_umount,
            'useradd': self.cmd_useradd,
            'userdel': self.cmd_userdel,
            'passwd': self.cmd_passwd,
            'su': self.cmd_su,
            'login': self.cmd_login,
            'logout': self.cmd_logout,
        }
    
    def get_commands(self) -> dict[str, Callable]:
        """Get all built-in commands."""
        return self._commands
    
    def is_builtin(self, name: str) -> bool:
        """Check if a command is built-in."""
        return name in self._commands
    
    def execute(self, name: str, args: List[str]) -> int:
        """
        Execute a built-in command.
        
        Args:
            name: Command name
            args: Command arguments
        
        Returns:
            Exit code
        """
        cmd = self._commands.get(name)
        if cmd:
            try:
                return cmd(args)
            except Exception as e:
                print(f"{name}: {e}")
                return 1
        return 127  # Command not found
    
    # Command implementations
    
    def cmd_help(self, args: List[str]) -> int:
        """Display help information."""
        help_text = """
PyOS Shell - Built-in Commands

File Operations:
  ls [path]         List directory contents
  cd <path>         Change directory
  pwd               Print working directory
  mkdir <path>      Create directory
  rmdir <path>      Remove empty directory
  touch <file>      Create empty file
  rm <file>         Remove file
  cat <file>        Display file contents
  chmod <mode> <file>  Change permissions
  chown <uid>:<gid> <file>  Change owner

Process Management:
  ps                List processes
  kill <pid> [signal]  Send signal to process

User Management:
  whoami            Display current user
  id                Display user/group IDs
  useradd <name>    Create user (root only)
  userdel <name>    Delete user (root only)
  passwd [user]     Change password
  su [user]         Switch user
  login             Login to system
  logout            Logout from session

System:
  uname [-a]        Display system information
  uptime            Display system uptime
  free              Display memory usage
  df                Display filesystem usage
  date              Display current date/time
  clear             Clear screen
  export VAR=val    Set environment variable
  env               Display environment

Shell:
  help              Display this help
  history           Display command history
  exit              Exit the shell
"""
        print(help_text)
        return 0
    
    def cmd_exit(self, args: List[str]) -> int:
        """Exit the shell."""
        self._shell.request_exit()
        return 0
    
    def cmd_ls(self, args: List[str]) -> int:
        """List directory contents."""
        kernel = self._shell.kernel
        if not kernel or not kernel.filesystem:
            print("ls: filesystem not available")
            return 1
        
        path = args[0] if args else self._shell.cwd
        uid = self._shell.current_uid
        gid = self._shell.current_gid
        
        try:
            entries = kernel.filesystem.readdir(path, self._shell.cwd)
            
            for entry in entries:
                if entry['name'] in ('.', '..'):
                    continue
                
                # Format: permissions size name
                if entry['type'] == 'DIRECTORY':
                    perm = 'd'
                else:
                    perm = '-'
                
                perm += 'r' if int(entry['mode'], 8) & 0o400 else '-'
                perm += 'w' if int(entry['mode'], 8) & 0o200 else '-'
                perm += 'x' if int(entry['mode'], 8) & 0o100 else '-'
                
                size = str(entry['size']).rjust(8)
                name = entry['name']
                
                if entry['type'] == 'DIRECTORY':
                    name += '/'
                
                print(f"{perm} {size} {name}")
            
            return 0
            
        except Exception as e:
            print(f"ls: {e}")
            return 1
    
    def cmd_cd(self, args: List[str]) -> int:
        """Change directory."""
        if not args:
            path = '/'
        else:
            path = args[0]
        
        kernel = self._shell.kernel
        if not kernel or not kernel.filesystem:
            print("cd: filesystem not available")
            return 1
        
        # Resolve path
        from pyos.filesystem.path_resolver import PathResolver
        resolved = PathResolver.resolve(path, self._shell.cwd)
        
        if kernel.filesystem.is_directory(resolved):
            self._shell.cwd = resolved
            return 0
        else:
            print(f"cd: {path}: No such directory")
            return 1
    
    def cmd_pwd(self, args: List[str]) -> int:
        """Print working directory."""
        print(self._shell.cwd)
        return 0
    
    def cmd_mkdir(self, args: List[str]) -> int:
        """Create directory."""
        if not args:
            print("mkdir: missing operand")
            return 1
        
        kernel = self._shell.kernel
        if not kernel or not kernel.filesystem:
            print("mkdir: filesystem not available")
            return 1
        
        for path in args:
            try:
                kernel.filesystem.mkdir(
                    path,
                    mode=0o755,
                    uid=self._shell.current_uid,
                    gid=self._shell.current_gid,
                    cwd=self._shell.cwd
                )
            except Exception as e:
                print(f"mkdir: cannot create directory '{path}': {e}")
                return 1
        
        return 0
    
    def cmd_rmdir(self, args: List[str]) -> int:
        """Remove empty directory."""
        if not args:
            print("rmdir: missing operand")
            return 1
        
        kernel = self._shell.kernel
        if not kernel or not kernel.filesystem:
            print("rmdir: filesystem not available")
            return 1
        
        for path in args:
            try:
                kernel.filesystem.rmdir(
                    path,
                    uid=self._shell.current_uid,
                    gid=self._shell.current_gid,
                    cwd=self._shell.cwd
                )
            except Exception as e:
                print(f"rmdir: failed to remove '{path}': {e}")
                return 1
        
        return 0
    
    def cmd_touch(self, args: List[str]) -> int:
        """Create empty file or update timestamp."""
        if not args:
            print("touch: missing file operand")
            return 1
        
        kernel = self._shell.kernel
        if not kernel or not kernel.filesystem:
            print("touch: filesystem not available")
            return 1
        
        for path in args:
            try:
                inode = kernel.filesystem.stat(path, self._shell.cwd)
                if inode:
                    inode.touch()
                else:
                    kernel.filesystem.create(
                        path,
                        mode=0o644,
                        uid=self._shell.current_uid,
                        gid=self._shell.current_gid,
                        cwd=self._shell.cwd
                    )
            except Exception as e:
                print(f"touch: cannot touch '{path}': {e}")
                return 1
        
        return 0
    
    def cmd_rm(self, args: List[str]) -> int:
        """Remove file."""
        if not args:
            print("rm: missing operand")
            return 1
        
        kernel = self._shell.kernel
        if not kernel or not kernel.filesystem:
            print("rm: filesystem not available")
            return 1
        
        for path in args:
            try:
                kernel.filesystem.unlink(
                    path,
                    uid=self._shell.current_uid,
                    gid=self._shell.current_gid,
                    cwd=self._shell.cwd
                )
            except Exception as e:
                print(f"rm: cannot remove '{path}': {e}")
                return 1
        
        return 0
    
    def cmd_cat(self, args: List[str]) -> int:
        """Display file contents."""
        if not args:
            print("cat: missing file operand")
            return 1
        
        kernel = self._shell.kernel
        if not kernel or not kernel.filesystem:
            print("cat: filesystem not available")
            return 1
        
        for path in args:
            try:
                inode = kernel.filesystem.stat(path, self._shell.cwd)
                if not inode:
                    print(f"cat: {path}: No such file")
                    return 1
                
                content = inode.read()
                print(content.decode('utf-8', errors='replace'))
            except Exception as e:
                print(f"cat: {path}: {e}")
                return 1
        
        return 0
    
    def cmd_echo(self, args: List[str]) -> int:
        """Echo arguments."""
        print(' '.join(args))
        return 0
    
    def cmd_ps(self, args: List[str]) -> int:
        """List processes."""
        kernel = self._shell.kernel
        if not kernel or not kernel.process_manager:
            print("ps: process manager not available")
            return 1
        
        processes = kernel.process_manager.list_processes()
        
        print(f"{'PID':>6} {'PPID':>6} {'STATE':<10} {'NAME':<20}")
        print("-" * 50)
        
        for proc in processes:
            print(f"{proc['pid']:>6} {proc['ppid']:>6} {proc['state']:<10} {proc['name']:<20}")
        
        return 0
    
    def cmd_kill(self, args: List[str]) -> int:
        """Send signal to process."""
        if not args:
            print("kill: usage: kill pid [signal]")
            return 1
        
        try:
            pid = int(args[0])
            signal = int(args[1]) if len(args) > 1 else 15
            
            kernel = self._shell.kernel
            if not kernel or not kernel.process_manager:
                print("kill: process manager not available")
                return 1
            
            from pyos.process.states import Signal
            sig = None
            for s in Signal:
                if s.value == signal:
                    sig = s
                    break
            
            if sig:
                kernel.process_manager.kill(pid, sig)
            else:
                print(f"kill: invalid signal: {signal}")
                return 1
            
            return 0
            
        except ValueError:
            print("kill: invalid pid")
            return 1
        except Exception as e:
            print(f"kill: {e}")
            return 1
    
    def cmd_chmod(self, args: List[str]) -> int:
        """Change file permissions."""
        if len(args) < 2:
            print("chmod: usage: chmod mode file")
            return 1
        
        try:
            mode = int(args[0], 8)
            path = args[1]
            
            kernel = self._shell.kernel
            if not kernel or not kernel.filesystem:
                print("chmod: filesystem not available")
                return 1
            
            kernel.filesystem.chmod(
                path, mode,
                uid=self._shell.current_uid,
                gid=self._shell.current_gid,
                cwd=self._shell.cwd
            )
            
            return 0
            
        except ValueError:
            print("chmod: invalid mode")
            return 1
        except Exception as e:
            print(f"chmod: {e}")
            return 1
    
    def cmd_chown(self, args: List[str]) -> int:
        """Change file owner."""
        if len(args) < 2:
            print("chown: usage: chown uid:gid file")
            return 1
        
        try:
            parts = args[0].split(':')
            uid = int(parts[0])
            gid = int(parts[1]) if len(parts) > 1 else 0
            path = args[1]
            
            kernel = self._shell.kernel
            if not kernel or not kernel.filesystem:
                print("chown: filesystem not available")
                return 1
            
            kernel.filesystem.chown(
                path, uid, gid,
                uid=self._shell.current_uid,
                cwd=self._shell.cwd
            )
            
            return 0
            
        except ValueError:
            print("chown: invalid uid:gid")
            return 1
        except Exception as e:
            print(f"chown: {e}")
            return 1
    
    def cmd_whoami(self, args: List[str]) -> int:
        """Display current username."""
        print(self._shell.current_user or 'root')
        return 0
    
    def cmd_id(self, args: List[str]) -> int:
        """Display user/group IDs."""
        uid = self._shell.current_uid
        gid = self._shell.current_gid
        
        kernel = self._shell.kernel
        if kernel and kernel.user_manager:
            user = kernel.user_manager.get_user(uid)
            username = user.username if user else str(uid)
            group = kernel.user_manager.get_group(gid)
            groupname = group.name if group else str(gid)
        else:
            username = str(uid)
            groupname = str(gid)
        
        print(f"uid={uid}({username}) gid={gid}({groupname})")
        return 0
    
    def cmd_uname(self, args: List[str]) -> int:
        """Display system information."""
        kernel = self._shell.kernel
        if not kernel:
            print("uname: kernel not available")
            return 1
        
        info = kernel.get_info()
        
        if '-a' in args:
            print(f"{info.name} {info.version} PyOS x86_64")
        else:
            print(info.name)
        
        return 0
    
    def cmd_clear(self, args: List[str]) -> int:
        """Clear screen."""
        print("\033[2J\033[H", end='')
        return 0
    
    def cmd_history(self, args: List[str]) -> int:
        """Display command history."""
        history = self._shell.parser.get_history()
        for i, cmd in enumerate(history, 1):
            print(f"{i:>5}  {cmd}")
        return 0
    
    def cmd_export(self, args: List[str]) -> int:
        """Set environment variable."""
        if not args:
            # Print all environment
            for key, value in self._shell.environ.items():
                print(f"{key}={value}")
            return 0
        
        for arg in args:
            if '=' in arg:
                key, value = arg.split('=', 1)
                self._shell.environ[key] = value
            else:
                print(f"export: invalid argument: {arg}")
        
        return 0
    
    def cmd_env(self, args: List[str]) -> int:
        """Display environment variables."""
        for key, value in self._shell.environ.items():
            print(f"{key}={value}")
        return 0
    
    def cmd_date(self, args: List[str]) -> int:
        """Display current date and time."""
        print(time.strftime('%a %b %d %H:%M:%S %Z %Y'))
        return 0
    
    def cmd_uptime(self, args: List[str]) -> int:
        """Display system uptime."""
        kernel = self._shell.kernel
        if not kernel:
            print("uptime: kernel not available")
            return 1
        
        uptime = kernel.uptime
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        
        print(f"up {hours:02d}:{minutes:02d}:{seconds:02d}")
        return 0
    
    def cmd_free(self, args: List[str]) -> int:
        """Display memory usage."""
        kernel = self._shell.kernel
        if not kernel or not kernel.memory_manager:
            print("free: memory manager not available")
            return 1
        
        stats = kernel.memory_manager.get_stats()
        total = stats['total']
        used = stats['used']
        free = stats['free']
        
        print(f"              total        used        free")
        print(f"Mem:     {total:>10}  {used:>10}  {free:>10}")
        
        return 0
    
    def cmd_df(self, args: List[str]) -> int:
        """Display filesystem usage."""
        kernel = self._shell.kernel
        if not kernel or not kernel.filesystem:
            print("df: filesystem not available")
            return 1
        
        stats = kernel.filesystem.get_stats()
        
        print(f"Filesystem     Size    Used   Avail  Use%")
        print(f"pyos-root   {stats['max_size']:>8} {stats['total_size']:>8} "
              f"{stats['max_size'] - stats['total_size']:>8} {stats['utilization']:>4.0f}%")
        
        return 0
    
    def cmd_mount(self, args: List[str]) -> int:
        """Mount filesystem (simulated)."""
        print("mount: simulated filesystem - no mount needed")
        return 0
    
    def cmd_umount(self, args: List[str]) -> int:
        """Unmount filesystem (simulated)."""
        print("umount: simulated filesystem - cannot unmount root")
        return 1
    
    def cmd_useradd(self, args: List[str]) -> int:
        """Create user."""
        if not args:
            print("useradd: missing username")
            return 1
        
        if self._shell.current_uid != 0:
            print("useradd: only root can create users")
            return 1
        
        kernel = self._shell.kernel
        if not kernel or not kernel.user_manager:
            print("useradd: user manager not available")
            return 1
        
        try:
            kernel.user_manager.create_user(args[0], 'password')
            print(f"useradd: user '{args[0]}' created")
            return 0
        except Exception as e:
            print(f"useradd: {e}")
            return 1
    
    def cmd_userdel(self, args: List[str]) -> int:
        """Delete user."""
        if not args:
            print("userdel: missing username")
            return 1
        
        if self._shell.current_uid != 0:
            print("userdel: only root can delete users")
            return 1
        
        kernel = self._shell.kernel
        if not kernel or not kernel.user_manager:
            print("userdel: user manager not available")
            return 1
        
        try:
            kernel.user_manager.delete_user(args[0])
            print(f"userdel: user '{args[0]}' deleted")
            return 0
        except Exception as e:
            print(f"userdel: {e}")
            return 1
    
    def cmd_passwd(self, args: List[str]) -> int:
        """Change password."""
        username = args[0] if args else self._shell.current_user
        
        print(f"Changing password for {username}")
        print("(simulated - enter any password)")
        
        try:
            old = input("(current) password: ")
            new = input("New password: ")
            confirm = input("Retype new password: ")
            
            if new != confirm:
                print("passwd: passwords do not match")
                return 1
            
            kernel = self._shell.kernel
            if kernel and kernel.user_manager:
                kernel.user_manager.change_password(username, old, new)
                print("passwd: password updated successfully")
            
            return 0
        except Exception as e:
            print(f"passwd: {e}")
            return 1
    
    def cmd_su(self, args: List[str]) -> int:
        """Switch user."""
        username = args[0] if args else 'root'
        
        kernel = self._shell.kernel
        if not kernel or not kernel.user_manager:
            print("su: user manager not available")
            return 1
        
        user = kernel.user_manager.get_user_by_name(username)
        if not user:
            print(f"su: user {username} does not exist")
            return 1
        
        print(f"Password: (simulated - enter any password)")
        password = input("")
        
        try:
            session = kernel.user_manager.login(username, password)
            self._shell.current_session = session
            self._shell.current_uid = user.uid
            self._shell.current_gid = user.gid
            self._shell.current_user = username
            
            print(f"Switched to user {username}")
            return 0
        except Exception as e:
            print(f"su: {e}")
            return 1
    
    def cmd_login(self, args: List[str]) -> int:
        """Login to system."""
        print("PyOS Login")
        username = input("Username: ")
        password = input("Password: ")
        
        kernel = self._shell.kernel
        if not kernel or not kernel.user_manager:
            print("login: user manager not available")
            return 1
        
        try:
            session = kernel.user_manager.login(username, password)
            user = kernel.user_manager.get_user_by_name(username)
            
            self._shell.current_session = session
            self._shell.current_uid = user.uid
            self._shell.current_gid = user.gid
            self._shell.current_user = username
            
            print(f"Welcome to PyOS, {username}!")
            return 0
        except Exception as e:
            print(f"login: {e}")
            return 1
    
    def cmd_logout(self, args: List[str]) -> int:
        """Logout from session."""
        kernel = self._shell.kernel
        if kernel and kernel.user_manager and self._shell.current_session:
            kernel.user_manager.logout(self._shell.current_session.session_id)
        
        # Reset to root
        self._shell.current_uid = 0
        self._shell.current_gid = 0
        self._shell.current_user = 'root'
        self._shell.current_session = None
        
        print("Logged out")
        return 0
