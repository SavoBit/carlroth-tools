"""ConsoleUtils.py
"""

import sys, os
import subprocess
import pexpect

PUBKEY = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDOKEwudWc+YZc2inn7EI+cytXRgPfH4VzvO7aRRhZ2HhAZVKRoYRVg5qf4KdOKwOKOUVcy3G/zQC++xE+O72m5yLcvncZ4cQoq7PZjKjpxCGUUcwqomSHVs1CH6/cMoPH3lTzuP8jkHV1YjTffedIOsNo3BowJkTMunCMtPuFN8pk0jNfyrYrTZ8oJi3NpuRjvyw/qYzBwLAetf6XobpwRZaY7NAx1uJa/VJA7FDiadHrDEGNmKdXO+jf72y8rHDTUVJ9+FXajfWEe0nqyNsVol8Lya8gQclZmwXUtXPt8ZnoORQCdlVAg14ZAeYeNJdBKNULpZIDs7Ys+BTMH0jIjy0Pqf7UzSPSJM+SmGRlKm/nzUy86jPXiknyyR9vAADU7hVxkCqc7dUHTYmv6uQqnoSFPK9IoMa8JhWTVqPjDYRP01wis79h8X3nnamVbDD+N0FWMzMp2WjKxA/E1u0VH1GB3Xon4yIIB0sCRek99xBu5MRUA+vh3/f62SheHdTTzy6z/8VBiMX1JXvHiBGP9nQ5shcRFA8XNvxbZJWwfm8SzNNQZxkTIDnHr6/A2Bt85t5ZZ2kvFMuml7EJc0KOWfNgIstFBNHPBJaJjdvFEjZikrYe/Jm0KD1daSEx6gd5YTCRYi1xileFp5d7PbrOXKrb7hZyidocI4s7gLA3vhw== Ursus SSH key"

ADMIN_USER = 'admin'
ADMIN_PASS = 'adminadmin'

def quote(s):
    """Quote a string so that it passes transparently through a shell."""

    q = ""
    for c in s:
        if c in """' ;{}()[]<>*#&|""":
            q += '''"'''
            q += c
            q += '''"'''
        elif c in '''"$`!''':
            q += """'"""
            q += c
            q += """'"""
        else:
            q += c
    return q

class PopenBase(subprocess.Popen):

    @classmethod
    def wrap_params(cls, *args, **kwargs):
        return args, kwargs

    def __init__(self, *args, **kwargs):
        args, kwargs = self.wrap_params(*args, **kwargs)
        super(PopenBase, self).__init__(*args, **kwargs)

class SubprocessBase(object):

    popen_klass = subprocess.Popen

    def call(self, *popenargs, **kwargs):
        return self.popen_klass(*popenargs, **kwargs).wait()

    def check_call(self, *popenargs, **kwargs):

        # try to break inheritance loop
        ##retcode = self.call(*popenargs, **kwargs)
        retcode = self.popen_klass(*popenargs, **kwargs).wait()

        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise subprocess.CalledProcessError(retcode, cmd)
        return 0

    def check_output(self, *popenargs, **kwargs):
        if 'stdout' in kwargs:
            raise ValueError('stdout argument not allowed, it will be overridden.')
        process = self.popen_klass(stdout=subprocess.PIPE, *popenargs, **kwargs)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise subprocess.CalledProcessError(retcode, cmd, output=output)
        return output

class SshPopen(PopenBase):

    @classmethod
    def wrap_params(cls, *args, **kwargs):

        kwargs = dict(kwargs)

        if args:
            cmd, args = args[0], args[1:]
        else:
            cmd = kwargs.pop('args', None)

        host = kwargs.pop('host')
        user = kwargs.pop('user')

        sshcmd = ['ssh',
                  '-F/dev/null',
                  '-oUser=%s' % user,
                  '-oStrictHostKeyChecking=no',
                  '-oUserKnownHostsFile=/dev/null',
                  '-oBatchMode=yes',
                  host,]

        tty = kwargs.pop('tty', None)
        if tty:
            sshcmd[2:2] = ['-oRequestTTY=force',]

        if cmd:
            sshcmd += ['--',]
            if isinstance(cmd, basestring):
                cmd = ['/bin/sh', '-c', quote('IFS=;' + cmd),]
            sshcmd += cmd

        args = (sshcmd,) + tuple(args)
        return super(SshPopen, cls).wrap_params(*args, **kwargs)

IN = "in"
OUT = "out"

class SshSubprocessBase(SubprocessBase):
    """Decorate subprocess commands with a host parameter."""

    def __init__(self, host, user):
        self.host = host
        self.user = user

    def call(self, *args, **kwargs):
        return super(SshSubprocessBase, self).call(*args, host=self.host, user=self.user, **kwargs)

    def check_call(self, *args, **kwargs):
        return super(SshSubprocessBase, self).check_call(*args, host=self.host, user=self.user, **kwargs)

    def check_output(self, *args, **kwargs):
        return super(SshSubprocessBase, self).check_output(*args, host=self.host, user=self.user, **kwargs)

    def check_scp(self, *args, **kwargs):
        """Copy to/from a controller.

        Set 'direction' to IN or OUT.
        Set 'host' to the remote source or dest host.
        Set *args to the file arguments, with the final source/dest
        as the last argument.
        """

        kwargs = dict(kwargs)
        _dir = kwargs.pop('direction')

        args = list(args)
        scpargs = []
        if _dir == IN:
            while len(args) > 1:
                scpargs.append(self.host + ':' + quote(args.pop(0)))
            scpargs.append(quote(args.pop(0)))
        elif _dir == OUT:
            while len(args) > 1:
                scpargs.append(quote(args.pop(0)))
            scpargs.append(self.host + ':' + quote(args.pop(0)))
        else:
            raise ValueError("invalid direction")

        scpcmd = ['scp',
                  '-F/dev/null',
                  '-oUser=%s' % self.user,
                  '-oStrictHostKeyChecking=no',
                  '-oUserKnownHostsFile=/dev/null',
                  '-oBatchMode=yes',]
        scpcmd += scpargs

        args = (scpcmd,) + tuple(args)
        subprocess.check_call(scpcmd)

class ControllerRootSubprocess(SshSubprocessBase):

    popen_klass = SshPopen

    def __init__(self, host):
        self.host = host
        self.user = 'root'

    def testBatchSsh(self):
        """Test that root SSH login is enabled.

        Returns 0 if successful.
        """
        try:
            code = self.check_call(('/bin/true',))
        except subprocess.CalledProcessError, what:
            code = what.returncode
        return True if code == 0 else False

class ControllerCliPopen(SshPopen):
    """Batch-mode access to controller cli commands."""

    @classmethod
    def wrap_params(cls, *args, **kwargs):

        kwargs = dict(kwargs)

        if args:
            cmd, args = args[0], args[1:]
        else:
            cmd = kwargs.pop('args', None)

        clicmd = ['sudo', '-u', ADMIN_USER,
                  '--',
                  'floodlight-cli',
                  '-I', '-X',
                  '-u', ADMIN_USER,
                  '-p', ADMIN_PASS,]

        mode = kwargs.pop('mode', None)
        if mode is not None:
            clicmd[5:5] = ['-m', mode,]

        if not cmd:
            # allow for (empty) interactive Cli
            pass
        elif isinstance(cmd, basestring):
            clicmd += ['-c', cmd,]
        else:
            qcmd = [quote(w) for w in cmd]
            clicmd += ['-c', '''" "'''.join(qcmd),]

        args = (clicmd,) + tuple(args)
        kwargs['tty'] = True
        return super(ControllerCliPopen, cls).wrap_params(*args, **kwargs)

class ControllerCliSubprocess(SshSubprocessBase):

    popen_klass = ControllerCliPopen

    def __init__(self, host, mode=None):
        self.host = host
        self.user = 'root'
        self.mode = mode

    def call(self, *args, **kwargs):
        return super(SshSubprocessBase, self).call(*args, host=self.host, user=self.user, mode=self.mode, **kwargs)

    def check_call(self, *args, **kwargs):
        return super(SshSubprocessBase, self).check_call(*args, host=self.host, user=self.user, mode=self.mode, **kwargs)

    def check_output(self, *args, **kwargs):
        return super(SshSubprocessBase, self).check_output(*args, host=self.host, user=self.user, mode=self.mode, **kwargs)

    def getSwitchAddress(self, switch):
        try:
            buf = self.check_output(('show', 'switch', switch, 'running-config',))
        except subprocess.CalledProcessError, what:
            return None
        lines = [x for x in buf.splitlines() if x.startswith("interface ma1 ip-address")]
        if not lines:
            return None
        addr = lines[0].strip().split()[3].partition('/')[0]
        return addr

class ControllerAdminPopen(PopenBase):
    """Interactive access to admin cli.

    Batch commands are not accepted here.
    """

    @classmethod
    def wrap_params(cls, *args, **kwargs):

        kwargs = dict(kwargs)

        if args:
            cmd, args = args[0], args[1:]
        else:
            cmd = kwargs.pop('args', None)

        if cmd:
            raise ValueError("command not accepted for admin shell")

        host = kwargs.pop('host')

        cmd = ('ssh',
               '-t',
               '-F/dev/null',
               '-oUser=%s' % ADMIN_USER,
               '-oUserKnownHostsFile=/dev/null',
               '-oStrictHostKeyChecking=no',
               '-oBatchMode=no',
               '-oPasswordAuthentication=yes',
               '-oChallengeResponseAuthentication=no',
               host,)

        args = (cmd,) + tuple(args)
        return super(ControllerAdminPopen, cls).wrap_params(*args, **kwargs)

class ControllerAdminSubprocess(SshSubprocessBase):

    popen_klass = ControllerAdminPopen

    def spawn(self, **kwargs):
        args, popenKwargs = self.popen_klass.wrap_params(host=self.host)
        if popenKwargs:
            raise ValueError("invalid keyword arguments from subprocess: %s" % popenKwargs)
        args = list(args)
        kwargs = dict(kwargs)
        if args:
            cmd = args.pop(0)
        else:
            cmd = kwargs.pop('args')
        if isinstance(cmd, basestring):
            cmd, rest = cmd, []
        else:
            cmd, rest = cmd[0], cmd[1:]
        return pexpect.spawn(cmd, list(rest), *args, logfile=sys.stdout, **kwargs)

    def enableRoot(self):
        """Enable root login via the admin login."""

        ctl = self.spawn()
        i = ctl.expect(["password: $", pexpect.TIMEOUT, pexpect.EOF,], timeout=10)
        if i != 0:
            raise pexepect.ExceptionPexpect("cannot get password prompt")

        ctl.sendline(ADMIN_PASS)
        i = ctl.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF], timeout=10)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get bash prompt")

        ctl.sendline("debug bash")
        i = ctl.expect(["[$] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=2)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get bash prompt")

        ctl.sendline("exec sudo bash -e")
        i = ctl.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=2)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get bash prompt")

        for cmd in (('stty', '-echo', 'rows', '10000', 'cols', '999',),
                    ('mkdir', '-p', '/root/.ssh',),
                    ('chmod', '0700', '/root/.ssh',),
                    ('touch', '/root/.ssh/authorized_keys',),
                    ('chmod', '0600', '/root/.ssh/authorized_keys',),
                    ('set', 'dummy', PUBKEY,),
                    ('shift',),
                    ('echo', '"$*"', ">>/root/.ssh/authorized_keys",),
                ):
            ctl.sendline(" ".join(cmd))
            i = ctl.expect(["[#] $", "[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=2)
            if i != 0:
                raise pexpect.ExceptionPexpect("command failed: %d" % i)

        return 0

class SwitchConnectSubprocessBase(SubprocessBase):
    """Decorate subprocess commands with a host and switch parameter."""

    def __init__(self, host, switch, mode=None):
        self.host = host
        self.switch = switch
        self.mode = mode

    def call(self, *args, **kwargs):
        return super(SwitchConnectSubprocessBase, self).call(*args,
                                                             host=self.host, switch=self.switch, mode=self.mode,
                                                             **kwargs)

    def check_call(self, *args, **kwargs):
        return super(SwitchConnectSubprocessBase, self).check_call(*args,
                                                                   host=self.host, switch=self.switch, mode=self.mode,
                                                                   **kwargs)

    def check_output(self, *args, **kwargs):
        return super(SwitchConnectSubprocessBase, self).check_output(*args,
                                                                     host=self.host, switch=self.switch, mode=self.mode,
                                                                     **kwargs)

class SwitchConnectPopen(ControllerCliPopen):
    """Connect to the switch Cli using the floodlight-cli 'connect switch' command."""

    @classmethod
    def wrap_params(self, *args, **kwargs):
        kwargs = dict(kwargs)
        host = kwargs.pop('host')

        kwargs.pop('mode', None)
        mode = 'enable'
        # initial controller connection in 'enable' mode

        switch = kwargs.pop('switch')
        return super(SwitchConnectPopen, self).wrap_params(*args, host=host, mode='enable', **kwargs)

class SwitchConnectCliSubprocess(SwitchConnectSubprocessBase):
    popen_klass = SwitchConnectPopen

    def spawn(self, **kwargs):
        """Connect to the controller cli, then to the switch Cli."""

        cliCmd = ('connect', 'switch', self.switch,)
        args, popenKwargs = self.popen_klass.wrap_params(cliCmd, host=self.host, switch=self.switch)
        if popenKwargs:
            raise ValueError("invalid keyword arguments from subprocess: %s" % popenKwargs)
        args = list(args)
        kwargs = dict(kwargs)
        if args:
            cmd = args.pop(0)
        else:
            cmd = kwargs.pop('args')
        if isinstance(cmd, basestring):
            cmd, rest = cmd, []
        else:
            cmd, rest = cmd[0], cmd[1:]
        sw = pexpect.spawn(cmd, list(rest), *args, logfile=sys.stdout, **kwargs)

        return sw

    def check_call(self, *args, **kwargs):
        """Send a single command to the switch Cli.

        Assume no mode changes here!
        """

        args = list(args)
        kwargs = dict(kwargs)
        if args:
            cmd = args.pop(0)
        else:
            cmd = kwargs.pop('args')

        sw = self.spawn()
        i = sw.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=2)
        if i != 0:
            raise subprocess.CalledProcessError(i,
                                                ('switch', 'connect', self.switch,),
                                                sw.before)

        sw.sendline("debug admin")
        i = sw.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=30)
        if i != 0:
            raise subprocess.CalledProcessError(i, ('debug', 'admin',), sw.before)

        if isinstance(cmd, basestring):
            sw.sendline(cmd)
        else:
            sw.sendline(" ".join(cmd))
        i = sw.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=30)
        if i != 0:
            raise subprocess.CalledProcessError(i, cmd, sw.before)

        sw.sendline('exit')
        i = sw.expect([pexpect.EOF, "[>] $", pexpect.TIMEOUT,], timeout=2)
        if i != 0:
            raise subprocess.CalledProcessError(i, ('exit',), sw.before)

        return 0

    def call(self, *args, **kwargs):
        try:
            return self.check_call(*args, **kwargs)
        except subprocess.CalledProcessError, what:
            return what.returncode

    def check_output(self, *args, **kwargs):

        args = list(args)
        kwargs = dict(kwargs)
        if args:
            cmd = args.pop(0)
        else:
            cmd = kwargs.pop('args')

        sw = self.spawn()
        i = sw.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=2)
        if i != 0:
            raise subprocess.CalledProcessError(i,
                                                ('switch', 'connect', self.switch,),
                                                sw.before)

        sw.sendline("debug admin")
        i = sw.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=30)
        if i != 0:
            raise subprocess.CalledProcessError(i, ('debug', 'admin',), sw.before)

        if isinstance(cmd, basestring):
            sw.sendline(cmd)
        else:
            sw.sendline(" ".join(cmd))
        i = sw.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=30)
        if i != 0:
            raise subprocess.CalledProcessError(i, cmd, sw.before)
        buf = sw.before

        sw.sendline('exit')
        i = sw.expect([pexpect.EOF, "[>] $", pexpect.TIMEOUT,], timeout=2)
        if i != 0:
            raise subprocess.CalledProcessError(i, ('exit',), buf+sw.before)

        return buf

    def enableRecovery2(self):
        """Enable recovery (root) login via SSH."""

        sw = self.spawn()
        i = sw.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=2)
        if i != 0:
            raise subprocess.CalledProcessError(i,
                                                ('switch', 'connect', self.switch,),
                                                sw.before)

        sw.sendline("debug admin")
        i = sw.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=2)
        if i != 0:
            raise subprocess.CalledProcessError(i, ('debug', 'admin',), sw.before)

        sw.sendline("enable")
        i = sw.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=2)
        if i != 0:
            raise subprocess.CalledProcessError(i, ('enable',), sw.before)

        # get ourselves into a bash environment where we can detect errors

        sw.sendline("debug bash")
        i = sw.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=2)
        if i != 0:
            raise subprocess.CalledProcessError(i, ('debug', 'bash',), sw.before)

        sw.sendline("exec bash -e")
        i = sw.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=2)
        if i != 0:
            raise subprocess.CalledProcessError(i, ('exec', 'bash', '-e',), sw.before)

        sw.sendline("PS1='BASH# '")
        i = sw.expect(["BASH[#] $", "[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=2)
        if i != 0:
            raise subprocess.CalledProcessError(i, ('PS1=...',), sw.before)

        sw.sendline("echo hello")
        i = sw.expect(["BASH[#] $", "[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=2)
        if i != 0:
            raise subprocess.CalledProcessError(i, ('echo', 'hello',), sw.before)

        for cmd in (('stty', '-echo', 'rows', '10000', 'cols', '999',),
                    ('userdel', '--force', 'recovery2', '||', ':',),
                    ('useradd',
                     '--create-home',
                     '--home-dir', '/var/run/recovery2',
                     '--non-unique', '--no-user-group', '--uid', '0', '--gid', '0',
                     'recovery2',),
                    ('mkdir', '-p', '/var/run/recovery2/.ssh',),
                    ('chmod', '0700', '/var/run/recovery2/.ssh',),
                    ('touch', '/var/run/recovery2/.ssh/authorized_keys',),
                    ('chmod', '0600', '/var/run/recovery2/.ssh/authorized_keys',),
                    ('set', 'dummy', PUBKEY,),
                    ('shift',),
                    ('echo', '"$*"', ">>/var/run/recovery2/.ssh/authorized_keys",),
                ):
            sw.sendline(" ".join(cmd))
            i = sw.expect(["BASH[#] $", "[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=2)
            if i != 0:
                raise subprocess.CalledProcessError(i, ('...',), sw.before)

        return 0

class SwitchRecovery2Subprocess(SshSubprocessBase):

    popen_klass = SshPopen

    def __init__(self, host):
        self.host = host
        self.user = 'recovery2'

    def testBatchSsh(self):
        """Test that root SSH login is enabled.

        Returns 0 if successful.
        """
        try:
            code = self.check_call(('/bin/true',))
        except subprocess.CalledProcessError, what:
            code = what.returncode
        return True if code == 0 else False

class SwitchPcliPopen(SshPopen):
    """Batch-mode access to switch pcli commands."""

    @classmethod
    def wrap_params(cls, *args, **kwargs):

        kwargs = dict(kwargs)

        if args:
            cmd, args = args[0], args[1:]
        else:
            cmd = kwargs.pop('args')

        clicmd = ['pcli', '--force-admin',]

        mode = kwargs.pop('mode', None)
        if mode is not None:
            clicmd[1:1] = ['-m', mode,]

        if not cmd:
            # allow for (empty) interactive Cli
            pass
        elif isinstance(cmd, basestring):
            clicmd += ['-c', cmd,]
        else:
            qcmd = [quote(w) for w in cmd]
            clicmd += ['-c', '''" "'''.join(qcmd),]

        args = (clicmd,) + tuple(args)
        kwargs['tty'] = True
        return super(SwitchPcliPopen, cls).wrap_params(*args, **kwargs)

class SwitchPcliSubprocess(SshSubprocessBase):

    popen_klass = SwitchPcliPopen

    def __init__(self, host, mode=None):
        self.host = host
        self.user = 'recovery2'
        self.mode = mode

    def call(self, *args, **kwargs):
        return super(SshSubprocessBase, self).call(*args, host=self.host, user=self.user, mode=self.mode, **kwargs)

    def check_call(self, *args, **kwargs):
        return super(SshSubprocessBase, self).check_call(*args, host=self.host, user=self.user, mode=self.mode, **kwargs)

    def check_output(self, *args, **kwargs):
        return super(SshSubprocessBase, self).check_output(*args, host=self.host, user=self.user, mode=self.mode, **kwargs)
