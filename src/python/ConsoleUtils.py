"""ConsoleUtils.py
"""

import sys, os, pwd
import subprocess
import pexpect
import re
import tempfile
import socket

import TrackUtils

def findPubKey():
    """Retrieve the SSH public key for switch communication.

    Set the key specifier in $TESTS_SSH_KEY

    - find the key
    - find its public component
    - make sure ssh-agent is running
    - make sure the key is unlocked
    """

    if 'TESTS_SSH_KEY' not in os.environ:
        raise ValueError("missing an SSH key specifier in $TEST_SSH_KEY")

    if 'SSH_AUTH_SOCK' not in os.environ:
        raise ValueError("no ssh-agent set up")

    keySpec = os.environ['TESTS_SSH_KEY']

    if not os.path.exists(keySpec):
        raise ValueError("SSH key file not found")
    if not os.path.exists(keySpec+'.pub'):
        raise ValueError("SSH public key file not found")

    # get the fingerprint
    buf = subprocess.check_output(('ssh-keygen', '-l', '-f', keySpec,))
    fpr = buf.strip().split()[1]

    sigs = subprocess.check_output(('ssh-add', '-l',))
    if fpr not in sigs:
        raise ValueError("SSH key is not in ssh-agent")

findPubKey()

def getPubKey():
    with open(os.environ['TESTS_SSH_KEY']+'.pub', "r") as fd:
        pubkey = fd.read().strip()
    return pubkey

def getIdentityArgs():
    ident = os.environ['TESTS_SSH_KEY']
    return ['-oIdentityFile=%s' % ident, '-oIdentitiesOnly=yes',]

ADMIN_USER = 'admin'
ADMIN_PASS = 'adminadmin'

TIMEOUT_BOOT = 180
TIMEOUT_LONG = 30
TIMEOUT_SHORT = 5
TIMEOUT_LOGIN = 10

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

def quotePcli(s, quote=""):
    """Pcli quoting rules are a bit different."""

    oq = quote
    q = ""
    for c in s:

        if not oq and c in """'""":
            oq = '''"'''
            q += c
            continue
        if oq == '''"''' and c in """'""":
            q += c
            continue
        if c in """'""":
            q += "\\"
            q += c
            continue

        if not oq and c in '''"''':
            oq = """'"""
            q += c
            continue
        if oq == """'""" and c in '''"''':
            q += c
            continue
        if c in '''"''':
            q += "\\"
            q += c
            continue

        if not oq and c in " ":
            oq = '''"'''
            q += c
            continue

        q += c

    return oq + q + oq

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

        topt = "-oConnectTimeout=%d" % TIMEOUT_SHORT
        sshcmd = ['ssh',
                  '-F/dev/null',
                  '-oUser=%s' % user,
                  '-oStrictHostKeyChecking=no',
                  '-oUserKnownHostsFile=/dev/null',
                  topt,
                  host,]

        sshcmd.extend(getIdentityArgs())

        if ':' in host:
            sshcmd[2:2] = ['-6',]

        tty = kwargs.pop('tty', None)
        if tty:
            sshcmd[2:2] = ['-oRequestTTY=force',]

        interactive = kwargs.pop('interactive', False)
        if interactive:
            sshcmd[2:2] = ['-oPasswordAuthentication=yes',
                           '-oChallengeResponseAuthentication=no',
                           '-oBatchMode=no',]
        else:
            sshcmd[2:2] = ['-oBatchMode=yes',]

        agent = kwargs.pop('agent', True)
        if not agent:
            sshcmd[2:2] = ['-oPubkeyAuthentication=no',]

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
        Set 'quote' to False to disable e.g. pattern quoting
        Set *args to the file arguments, with the final source/dest
        as the last argument.
        """

        kwargs = dict(kwargs)
        _dir = kwargs.pop('direction')

        args = list(args)
        scpargs = []

        host = self.host
        if ':' in host:
            host = '[' + host + ']'
            scpargs.append('-6')

        _q = kwargs.pop('quote', True)
        if _q:
            qf = quote
        else:
            qf = lambda x: x

        if _dir == IN:
            while len(args) > 1:
                scpargs.append(host + ':' + qf(args.pop(0)))
            scpargs.append(qf(args.pop(0)))
        elif _dir == OUT:
            while len(args) > 1:
                scpargs.append(qf(args.pop(0)))
            scpargs.append(host + ':' + qf(args.pop(0)))
        else:
            raise ValueError("invalid direction")

        scpcmd = ['scp',
                  '-F/dev/null',
                  '-oUser=%s' % self.user,
                  '-oStrictHostKeyChecking=no',
                  '-oUserKnownHostsFile=/dev/null',
                  '-oBatchMode=yes',]
        scpcmd += scpargs

        scpcmd.extend(getIdentityArgs())

        args = (scpcmd,) + tuple(args)
        subprocess.check_call(scpcmd)

    def testBatchSsh(self):
        """Test that root SSH login is enabled.

        Returns 0 if successful.
        """
        try:
            code = self.check_call(('/bin/true',),
                                   tty=False, interactive=False)
        except subprocess.CalledProcessError, what:
            code = what.returncode
        return True if code == 0 else False

class ControllerRootSubprocess(SshSubprocessBase):

    popen_klass = SshPopen
    USER = 'root'

    def __init__(self, host, user=None):
        self.host = host
        self.user = user or self.USER

class ControllerCliPopen(SshPopen):
    """Batch-mode access to controller cli commands."""

    USER = ADMIN_USER
    PASS = ADMIN_PASS

    @classmethod
    def wrap_params(cls, *args, **kwargs):

        kwargs = dict(kwargs)

        if args:
            cmd, args = args[0], args[1:]
        else:
            cmd = kwargs.pop('args', None)

        clicmd = ['sudo', '-u', cls.USER,
                  '--',
                  'floodlight-cli',
                  '-I', '-X',
                  '-u', cls.USER,
                  '-p', cls.PASS,]

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

CLI_WARN_RE = re.compile("^[a-z_ ]+: .*$")

def parseCliTableRow(legend, sep, data):

    cols = [x for x in enumerate(sep) if x[1] == '|']
    cols = [x[0] for x in cols]
    m = {}
    p = 0
    idx = None
    while cols:
        q = cols.pop(0)
        key = legend[p:q].strip()
        val = data[p:q].strip()
        if key == '#':
            idx = int(val)
        else:
            m[key] = val
        p = q+1

    if idx is None:
        raise ValueError("invalid data: %s" % data)

    return idx, m

def parseCliTable(buf):

    lines = buf.strip().splitlines()
    while lines:
        line = lines[0]
        if line.startswith('#'):
            break
        if ':' in line:
            sys.stderr.write(lines.pop(0) + "\n")
        elif line == 'None.':
            return []
        else:
            raise ValueError("invalid cli output: %s" % line)

    legend, sep, rest = lines[0], lines[1], lines[2:]
    m = {}
    sz = -sys.maxint
    while rest:
        idx, rec = parseCliTableRow(legend, sep, rest.pop(0))
        m[idx] = rec
        sz = max(sz, idx)

    l = [{}] * sz
    for key, val in m.iteritems():
        l[key-1] = val

    return l

def parseCliDetail(buf):
    m = {}
    for line in buf.strip().splitlines():
        p = line.find(' : ')
        if p > -1:
            key = line[:p].strip()
            val = line[p+3:].strip()
            m[key] = val
        else:
            sys.stderr.write(line + "\n")
    return m

def parseCliTables(buf):
    m = {}
    while buf:

        if not buf.startswith('~'):
            raise ValueError("extra data: %s" % buf)

        line, sep, buf = buf.partition("\n")
        if not sep:
            raise ValueError("extra data: %s" % line)

        title = line.strip().strip('~').strip()

        p = buf.find("\n~")
        if p > -1:
            m[title] = parseCliTable(buf[:p])
            buf = buf[p+1:]
        else:
            m[title] = parseCliTable(buf)
            buf = ""

    return m

class CopyOutContext(object):

    def __init__(self, cli, src):
        self.cli = cli
        self.src = src
        self.dst = None

    def __enter__(self):

        self.dst = tempfile.mktemp()
        dstArg = "scp://bsn@localhost:%s" % (self.dst,)

        self.cli.copy(self.src, dstArg)

        uname = pwd.getpwuid(os.getuid()).pw_name
        subprocess.check_call(('sudo', 'chown', '-v', uname, self.dst,))

        # HURR https://bigswitch.atlassian.net/browse/SWL-3613
        # See also $SWL/packages/base/all/pcli/startup-config.init
        os.chmod(self.dst, 0644)

        return self

    def __exit__(self, typ, val, tb):

        if self.dst and os.path.exists(self.dst):
            subprocess.check_call(('sudo', 'rm', '-v', '-f', self.dst,))

        return None

class ControllerCliMixin:

    def getSwitchAddress(self, switch):

        # try to get the IPAM address
        try:
            buf = self.check_output(('show', 'switch', switch, 'running-config',))
        except subprocess.CalledProcessError, what:
            buf = None
        if buf:
            lines = [x for x in buf.splitlines() if x.startswith("interface ma1 ip-address")]
        else:
            lines = []
        if lines:
            addr = lines[0].strip().split()[3].partition('/')[0]
            if addr != '0.0.0.0':
                l, s, r = addr.partition('%')
                if s:
                    addr = "%s%%%s" % (l, TrackUtils.getDefaultV6Intf(),)
                return addr

        # else use the link local address
        rec = self.getSwitch(switch)
        addr = rec.get('IP Address', None)
        if addr is not None:
            l, s, r = addr.partition('%')
            if s:
                addr = "%s%%%s" % (l, TrackUtils.getDefaultV6Intf(),)
            return addr

        # else, use the mac address
        mac = rec.get('Switch MAC Address', None)
        if mac is not None:
            return TrackUtils.getV6AddrFromMac(mac)

        return None

    def getSwitch(self, switch):

        try:
            buf = self.check_output(('show', 'switch', switch,))
        except subprocess.CalledProcessError, what:
            buf = None
        if not buf: return {}
        return parseCliTable(buf)[0]

    def getCpsecStatus(self):
        try:
            buf = self.check_output(('show', 'secure', 'control', 'plane',))
        except subprocess.CalledProcessError, what:
            buf = None
        if not buf: return {}

        # split into constituent tables
        m = {}
        p = buf.find("\n~")
        if p < 0:
            raise ValueError("invalid cpsec output")
        m['detail'] = parseCliDetail(buf[:p])
        buf = buf[p+1:]
        m.update(parseCliTables(buf))
        return m

    def copy(self, src, dst):
        """Run the Cli 'copy' command."""

        sp = self.spawn()

        i = sp.expect(["# $", pexpect.TIMEOUT, pexpect.EOF], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise ValueError("expect failed: %s" % sp.before)

        sp.sendline("copy %s %s" % (src, dst,))

        i = sp.expect(["password: $", "# $", pexpect.TIMEOUT, pexpect.EOF], timeout=TIMEOUT_SHORT)
        if i == 0:
            sp.sendline("bsn")
            i = sp.expect(["# $", pexpect.TIMEOUT, pexpect.EOF], timeout=TIMEOUT_SHORT)
            if i != 0:
                raise ValueError("expect failed: %s" % sp.before)
        elif i != 1:
            raise ValueError("expect failed: %s" % sp.before)

        # exit to "enable"
        sp.sendline("exit")

        i = sp.expect(["# $", pexpect.TIMEOUT, pexpect.EOF], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise ValueError("expect failed: %s" % sp.before)

        # exit to normal
        sp.sendline("exit")

        i = sp.expect(["> $", pexpect.TIMEOUT, pexpect.EOF], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise ValueError("expect failed: %s" % sp.before)

        sp.sendline("exit")

        i = sp.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise ValueError("expect failed: %s" % sp.before)

    def copyOut(self, src):
        return CopyOutContext(self, src)

class ControllerCliSubprocess(ControllerCliMixin,
                              SshSubprocessBase):

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

class ControllerAdminPopen(SshPopen):
    """Interactive access to admin cli.

    Batch commands are not accepted here.
    """

    USER = ADMIN_USER

    @classmethod
    def wrap_params(cls, *args, **kwargs):

        kwargs = dict(kwargs)

        if args:
            cmd, args = args[0], args[1:]
        else:
            cmd = kwargs.pop('args', None)

        kwargs.setdefault('tty', True)
        kwargs.setdefault('interactive', True)
        kwargs.setdefault('user', cls.USER)
        if cmd and kwargs['user'] == ADMIN_USER:
            raise ValueError("command not accepted for admin shell")

        return super(ControllerAdminPopen, cls).wrap_params(cmd, *args, **kwargs)

class ControllerAdminSubprocess(SshSubprocessBase):

    USER = ADMIN_USER
    PASS = ADMIN_PASS

    popen_klass = ControllerAdminPopen

    def __init__(self, host, user=USER):
        super(ControllerAdminSubprocess, self).__init__(host, user)

    def spawn(self, **kwargs):
        kwargs = dict(kwargs)
        agent = kwargs.pop('agent', True)
        args, popenKwargs = self.popen_klass.wrap_params(host=self.host,
                                                         agent=agent)
        if popenKwargs:
            raise ValueError("invalid keyword arguments from subprocess: %s" % popenKwargs)
        args = list(args)
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

        ctl = self.spawn(agent=False)
        i = ctl.expect(["password: $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_LOGIN)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get password prompt")

        ctl.sendline(self.PASS)
        i = ctl.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF], timeout=TIMEOUT_LOGIN)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get bash prompt")

        ctl.sendline("debug bash")
        i = ctl.expect(["[$] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get bash prompt")

        ctl.sendline("exec sudo bash -e")
        i = ctl.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get bash prompt")

        for cmd in (('stty', '-echo', 'rows', '10000', 'cols', '999',),

                    ('chmod', '0755', '/root',),
                    # hm, this was a recent change, appears to be a
                    # security vuln.

                    ('mkdir', '-p', '/root/.ssh',),
                    ('chmod', '0700', '/root/.ssh',),
                    ('touch', '/root/.ssh/authorized_keys',),
                    ('chmod', '0600', '/root/.ssh/authorized_keys',),
                    ('set', 'dummy', getPubKey(),),
                    ('shift',),
                    ('echo', '"$*"', ">>/root/.ssh/authorized_keys",),
                ):
            ctl.sendline(" ".join(cmd))
            i = ctl.expect(["[#] $", "[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
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

class SwitchConnectMixin:

    def spawn(self, **kwargs):
        """Connect to the controller cli, then to the switch Cli."""

        cliCmd = ('connect', 'switch', self.switch,)
        args, popenKwargs = self.popen_klass.wrap_params(cliCmd,
                                                         host=self.host, user='root',
                                                         switch=self.switch)
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
        i = sw.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise subprocess.CalledProcessError(i,
                                                ('connect', 'switch', self.switch,),
                                                sw.before)

        sw.sendline("debug admin")
        i = sw.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_LONG)
        if i != 0:
            raise subprocess.CalledProcessError(i, ('debug', 'admin',), sw.before)

        if isinstance(cmd, basestring):
            sw.sendline(cmd)
        else:
            sw.sendline(" ".join(cmd))
        i = sw.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_LONG)
        if i != 0:
            raise subprocess.CalledProcessError(i, cmd, sw.before)

        sw.sendline('exit')
        i = sw.expect([pexpect.EOF, "[>] $", pexpect.TIMEOUT,], timeout=TIMEOUT_SHORT)
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
        i = sw.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise subprocess.CalledProcessError(i,
                                                ('connect', 'switch', self.switch,),
                                                sw.before)

        sw.sendline("debug admin")
        i = sw.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_LONG)
        if i != 0:
            raise subprocess.CalledProcessError(i, ('debug', 'admin',), sw.before)

        if isinstance(cmd, basestring):
            sw.sendline(cmd)
        else:
            sw.sendline(" ".join(cmd))
        i = sw.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_LONG)
        if i != 0:
            raise subprocess.CalledProcessError(i, cmd, sw.before)
        buf = sw.before

        sw.sendline('exit')
        i = sw.expect([pexpect.EOF, "[>] $", pexpect.TIMEOUT,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise subprocess.CalledProcessError(i, ('exit',), buf+sw.before)

        return buf

    def enableRecovery2(self):
        """Enable recovery (root) login via SSH."""

        sw = self.spawn()
        i = sw.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            sys.stderr.write("i %d\n" % i)
            sys.stderr.write("before %s\n" % sw.before)
            raise subprocess.CalledProcessError(i,
                                                ('connect', 'switch', self.switch,),
                                                sw.before)

        sw.sendline("debug admin")
        i = sw.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise subprocess.CalledProcessError(i, ('debug', 'admin',), sw.before)

        sw.sendline("enable")
        i = sw.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise subprocess.CalledProcessError(i, ('enable',), sw.before)

        # get ourselves into a bash environment where we can detect errors

        sw.sendline("debug bash")
        i = sw.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise subprocess.CalledProcessError(i, ('debug', 'bash',), sw.before)

        sw.sendline("exec bash -e")
        i = sw.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise subprocess.CalledProcessError(i, ('exec', 'bash', '-e',), sw.before)

        sw.sendline("PS1='BASH# '")
        i = sw.expect(["BASH[#] $", "[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise subprocess.CalledProcessError(i, ('PS1=...',), sw.before)

        sw.sendline("echo hello")
        i = sw.expect(["BASH[#] $", "[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
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
                    ('set', 'dummy', getPubKey(),),
                    ('shift',),
                    ('echo', '"$*"', ">>/var/run/recovery2/.ssh/authorized_keys",),
                ):
            sw.sendline(" ".join(cmd))
            i = sw.expect(["BASH[#] $", "[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
            if i != 0:
                raise subprocess.CalledProcessError(i, ('...',), sw.before)

        return 0

class SwitchConnectCliSubprocess(SwitchConnectMixin, SwitchConnectSubprocessBase):
    popen_klass = SwitchConnectPopen

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

    USER = "recovery2"

    @classmethod
    def wrap_params(cls, *args, **kwargs):

        kwargs = dict(kwargs)

        if args:
            cmd, args = args[0], args[1:]
        else:
            cmd = kwargs.pop('args', [])

        clicmd = ['pcli', '--debug', '-u', 'admin',]

        mode = kwargs.pop('mode', None)
        if mode is not None:
            clicmd[1:1] = ['-m', mode,]

        if not cmd:
            # allow for (empty) interactive Cli
            pass
        elif isinstance(cmd, basestring):
            clicmd += ['-c', quote(cmd),]
        else:
            qcmd = [quote(w) for w in cmd]
            clicmd += ['-c', '''" "'''.join(qcmd),]

        args = (clicmd,) + tuple(args)
        kwargs['tty'] = True
        return super(SwitchPcliPopen, cls).wrap_params(*args, **kwargs)

class SwitchPcliSubprocess(SshSubprocessBase):

    popen_klass = SwitchPcliPopen

    def __init__(self, host, user=None, mode=None):
        self.host = host
        self.user = user or self.popen_klass.USER
        self.mode = mode

    def call(self, *args, **kwargs):
        return super(SshSubprocessBase, self).call(*args, host=self.host, user=self.user, mode=self.mode, **kwargs)

    def check_call(self, *args, **kwargs):
        return super(SshSubprocessBase, self).check_call(*args, host=self.host, user=self.user, mode=self.mode, **kwargs)

    def check_output(self, *args, **kwargs):
        return super(SshSubprocessBase, self).check_output(*args, host=self.host, user=self.user, mode=self.mode, **kwargs)

class ControllerWorkspaceCliPopen(PopenBase):
    """Batch-mode access to controller cli commands.

    Drive a local controller instance that is running in this workspace.
    """

    RUNCLI = None
    ##RUNCLI = "%s/work/controller/bvs/runcli" % os.environ['HOME']
    # no equivalent to $SWITCHLIGHT for controller workspaces

    @classmethod
    def wrap_params(cls, *args, **kwargs):

        kwargs = dict(kwargs)

        if args:
            cmd, args = args[0], args[1:]
        else:
            cmd = kwargs.pop('args', None)

        if cls.RUNCLI is None:
            raise NotImplementedError("missing RUNCLI")

        clicmd = [cls.RUNCLI,]

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
            clicmd += ['-c', " ".join(qcmd),]

        args = (clicmd,) + tuple(args)

        # ha ha, runcli needs to run in-place
        if 'cwd' in kwargs:
            raise ValueError("pwd not supported")
        kwargs['cwd'] = os.path.dirname(cls.RUNCLI)

        return super(ControllerWorkspaceCliPopen, cls).wrap_params(*args, **kwargs)

class ControllerWorkspaceCliSubprocess(ControllerCliMixin,
                                       SubprocessBase):

    popen_klass = ControllerWorkspaceCliPopen

    def spawn(self, **kwargs):

        args, popenKwargs = self.popen_klass.wrap_params()

        cwd = popenKwargs.pop('cwd', None)
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

        if 'cwd' in kwargs:
            raise ValueError("cwd not supported")
        if cwd:
            kwargs['cwd'] = cwd

        return pexpect.spawn(cmd, list(rest), *args, logfile=sys.stdout, **kwargs)

class WorkspaceSwitchConnectSubprocessBase(SubprocessBase):
    """Decorate subprocess commands with a switch parameter."""

    def __init__(self, switch, mode=None):
        self.switch = switch
        self.mode = mode

    def call(self, *args, **kwargs):
        return super(WorkspaceSwitchConnectSubprocessBase, self).call(*args,
                                                                      switch=self.switch, mode=self.mode,
                                                                      **kwargs)

    def check_call(self, *args, **kwargs):
        return super(WorkspaceSwitchConnectSubprocessBase, self).check_call(*args,
                                                                            switch=self.switch, mode=self.mode,
                                                                            **kwargs)

    def check_output(self, *args, **kwargs):
        return super(WorkspaceSwitchConnectSubprocessBase, self).check_output(*args,
                                                                              switch=self.switch, mode=self.mode,
                                                                              **kwargs)
class WorkspaceSwitchConnectPopen(ControllerWorkspaceCliPopen):

    @classmethod
    def wrap_params(self, *args, **kwargs):
        kwargs = dict(kwargs)

        kwargs.pop('mode', None)
        mode = 'enable'
        # initial controller connection in 'enable' mode

        switch = kwargs.pop('switch')
        return super(WorkspaceSwitchConnectPopen, self).wrap_params(*args, mode='enable', **kwargs)

class WorkspaceSwitchConnectCliSubprocess(SwitchConnectMixin,
                                          WorkspaceSwitchConnectSubprocessBase):

    popen_klass = WorkspaceSwitchConnectPopen

    def spawn(self, **kwargs):
        """Connect to the controller cli, then to the switch Cli.

        When using the workspace controller, the host argument is not needed.
        """

        cliCmd = ('connect', 'switch', self.switch,)
        args, popenKwargs = self.popen_klass.wrap_params(cliCmd, switch=self.switch)

        cwd = popenKwargs.pop('cwd', None)
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

        if 'cwd' in kwargs:
            raise ValueError("cwd not supported")
        if cwd:
            kwargs['cwd'] = cwd

        sw = pexpect.spawn(cmd, list(rest), *args, logfile=sys.stdout, **kwargs)

        return sw

class SwitchInternalSshPopen(ControllerAdminPopen):
    USER = "root"
    PASS = "bsn"

class SwitchInternalSshSubprocess(SshSubprocessBase):

    popen_klass = SwitchInternalSshPopen

    def __init__(self, host, user=None):
        self.host = host
        self.user = user or self.popen_klass.USER

    def spawn(self, **kwargs):
        kwargs = dict(kwargs)
        agent = kwargs.pop('agent', True)
        args, popenKwargs = self.popen_klass.wrap_params(host=self.host,
                                                         agent=agent)
        if popenKwargs:
            raise ValueError("invalid keyword arguments from subprocess: %s" % popenKwargs)
        args = list(args)
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

        ctl = self.spawn(agent=False)
        i = ctl.expect(["password: $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_LOGIN)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get password prompt")

        ctl.sendline(self.popen_klass.PASS)
        i = ctl.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF], timeout=TIMEOUT_LOGIN)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get bash prompt")

        ctl.sendline("exec bash -e")
        i = ctl.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get bash prompt")

        for cmd in (('stty', '-echo', 'rows', '10000', 'cols', '999',),

                    ('chmod', '0755', '/root',),
                    # hm, this was a recent change, appears to be a
                    # security vuln.

                    ('mkdir', '-p', '/root/.ssh',),
                    ('chmod', '0700', '/root/.ssh',),
                    ('touch', '/root/.ssh/authorized_keys',),
                    ('chmod', '0600', '/root/.ssh/authorized_keys',),
                    ('set', 'dummy', getPubKey(),),
                    ('shift',),
                    ('echo', '"$*"', ">>/root/.ssh/authorized_keys",),
                ):
            ctl.sendline(" ".join(cmd))
            i = ctl.expect(["[#] $", "[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
            if i != 0:
                raise pexpect.ExceptionPexpect("command failed: %d" % i)

        return 0

class TrackConsolePopen(PopenBase):

    USER = "admin"

    ##USER = "root"
    ##PASS = "onl"

ADDR_RE = re.compile("IPv4 Address[(]es[)]: [0-9.]+")

class TrackConsoleSubprocess(SubprocessBase):

    popen_klass = TrackConsolePopen

    def __init__(self, host):
        self.host = host
        self.loginBanner = None

    def spawn(self, **kwargs):
        """Connect to the switch admin cli."""

        cliCmd = ('track', 'console', self.host,)
        args, popenKwargs = self.popen_klass.wrap_params(cliCmd)
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

    def _findLogin(self, sp):
        """back out iteratively to get to a login prompt"""

        for cnt in range(5):

            sp.sendline("")

            i = sp.expect(["login: $", "[#>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
            if i == 0: break

            sp.send(chr(0x4))

        sp.sendline("")

        i = sp.expect(["login: $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get admin prompt")

        self.loginBanner = sp.before

        return True

    def _dhcp(self, sp):

        # query the interface setup
        sp.sendline("show interface ma1")

        i = sp.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get admin prompt")

        m = ADDR_RE.search(sp.before)
        if m: return

        sp.sendline("config")

        i = sp.expect(["[(]config[)][#] $", pexpect.TIMEOUT, pexpect.EOF], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get config prompt")

        sp.sendline("interface ma1 ip-address dhcp")

        i = sp.expect(["[(]config[)][#] $", pexpect.TIMEOUT, pexpect.EOF], timeout=TIMEOUT_LOGIN)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get config prompt")

        sp.sendline("exit")

        i = sp.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF], timeout=TIMEOUT_LOGIN)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get enable prompt")

    def _enableSwlRoot(self, sp):

        sp.sendline("")

        i = sp.expect(["login: $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get admin prompt")

        sp.sendline(self.popen_klass.USER)

        i = sp.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_LOGIN)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get admin prompt")

        # always to go debug admin
        sp.sendline("debug admin")

        i = sp.expect(["Switching to debug admin mode", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_LOGIN)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get debug admin banner")

        i = sp.expect(["[>] $", pexpect.TIMEOUT, pexpect.EOF], timeout=TIMEOUT_LOGIN)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get debug admin prompt")

        sp.sendline("enable")

        i = sp.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get enable prompt")

        self._dhcp(sp)

        sp.sendline("debug bash")

        i = sp.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get bash prompt")

        sp.sendline("exec bash -e")
        i = sp.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get bash prompt")

        for cmd in (('stty', '-echo', 'rows', '10000', 'cols', '999',),

                    ('chmod', '0755', '/root',),
                    # hm, this was a recent change, appears to be a
                    # security vuln.

                    ('mkdir', '-p', '/root/.ssh',),
                    ('chmod', '0700', '/root/.ssh',),
                    ('touch', '/root/.ssh/authorized_keys',),
                    ('chmod', '0600', '/root/.ssh/authorized_keys',),
                    ('set', 'dummy', getPubKey(),),
                    ('shift',),
                    ('echo', '"$*"', ">>/root/.ssh/authorized_keys",),
                ):
            sp.sendline(" ".join(cmd))
            i = sp.expect(["[#] $", "[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
            if i != 0:
                raise pexpect.ExceptionPexpect("command failed: %d" % i)

    def _enableOnlRoot(self, sp):

        sp.sendline("")

        i = sp.expect(["login: $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get admin prompt")

        sp.sendline(self.popen_klass.USER)

        i = sp.expect(["[pP]assword: $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_LOGIN)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get password prompt")

        sp.sendline(self.popen_klass.PASS)
        i = sp.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF], timeout=TIMEOUT_LOGIN)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get bash prompt")

        sp.sendline("exec bash -e")
        i = sp.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get bash prompt")

        for cmd in (('stty', '-echo', 'rows', '10000', 'cols', '999',),

                    ('chmod', '0755', '/root',),
                    # hm, this was a recent change, appears to be a
                    # security vuln.

                    ('mkdir', '-p', '/root/.ssh',),
                    ('chmod', '0700', '/root/.ssh',),
                    ('touch', '/root/.ssh/authorized_keys',),
                    ('chmod', '0600', '/root/.ssh/authorized_keys',),
                    ('set', 'dummy', getPubKey(),),
                    ('shift',),
                    ('echo', '"$*"', ">>/root/.ssh/authorized_keys",),
                ):
            sp.sendline(" ".join(cmd))
            i = sp.expect(["[#] $", "[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
            if i != 0:
                raise pexpect.ExceptionPexpect("command failed: %d" % i)

    def enableRoot(self):
        """Enable root login via the admin login

        Along the way, enable the management interface.
        """
        ctl = self.spawn()

        if not self._findLogin(ctl):
            raise pexpect.ExceptionPexpect("cannot get login prompt")

        if 'SWL' in self.loginBanner:
            self.popen_klass.USER = 'admin'
            self._enableSlRoot(ctl)
        elif 'ONL' in self.loginBanner:
            try:
                u, self.popen_class.USER = self.popen_klass.USER, 'root'
                p, self.popen_klass.PASS = self.popen_klass.PASS, 'onl'
                self._enableOnlRoot(ctl)
            finally:
                self.popen_klass.USER = u
                self.popen_klass.PASS = p
        else:
            raise pexpect.ExceptionPexpect("invalid login banner")

        # log back out
        self._findLogin(ctl)

        return 0

    def reboot(self):
        """Power-cycle the box.

        Use this if a normal 'reboot' from the root account is not possible.
        """
        cliCmd = ('track', 'power', self.host, 'reboot',)
        subprocess.check_call(cliCmd)

    def _waitUboot(self, sp):
        """Wait for the uboot prompt.

        Assume that the system was just rebooted.
        """

        i = sp.expect(["Hit any key to stop autoboot: ", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_BOOT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get uboot prompt")

        sp.sendline("")

        i = sp.expect(["> $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get uboot prompt")

    def _findUbootOnieRescue(self, sp):
        """Boot to the ONIE rescue prompt."""

        sp.sendline("")

        i = sp.expect(["> $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get uboot prompt")

        sp.sendline("run onie_rescue")

        i = sp.expect(["Please press Enter", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_BOOT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get ONIE prompt")

        sp.sendline("")

        i = sp.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get ONIE prompt")

    def _installOnieUrl(self, sp, url):

        sp.sendline("")

        i = sp.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get ONIE prompt")

        sp.sendline("read url")
        sp.sendline(url)

        i = sp.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get ONIE prompt")

        sp.sendline("install_url $url")

        i = sp.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i == 0:
            raise pexpect.ExceptionPexpect("cannot start download")

        # wait for the login prompt

        i = sp.expect(["login: $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_LONG0)
        if i != 0:
            raise pexpect.ExceptionPexpect("URL install failed")

class SwitchRootSubprocess(SshSubprocessBase):

    popen_klass = SwitchInternalSshPopen

    def __init__(self, host, user=None):
        user = user or self.popen_klass.USER
        SshSubprocessBase.__init__(self, host, user=user)

    def spawn(self, **kwargs):
        kwargs = dict(kwargs)
        agent = kwargs.pop('agent', False)
        args, popenKwargs = self.popen_klass.wrap_params(host=self.host,
                                                         agent=agent)
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

        ctl = self.spawn(agent=False)
        i = ctl.expect(["password: $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_LOGIN)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get password prompt")

        ctl.sendline(self.popen_klass.PASS)
        i = ctl.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF], timeout=TIMEOUT_LOGIN)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get bash prompt")

        ctl.sendline("exec sudo bash -e")
        i = ctl.expect(["[#] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
        if i != 0:
            raise pexpect.ExceptionPexpect("cannot get bash prompt")

        for cmd in (('stty', '-echo', 'rows', '10000', 'cols', '999',),

                    ('chmod', '0755', '/root',),
                    # hm, this was a recent change, appears to be a
                    # security vuln.

                    ('mkdir', '-p', '/root/.ssh',),
                    ('chmod', '0700', '/root/.ssh',),
                    ('touch', '/root/.ssh/authorized_keys',),
                    ('chmod', '0600', '/root/.ssh/authorized_keys',),
                    ('set', 'dummy', getPubKey(),),
                    ('shift',),
                    ('echo', '"$*"', ">>/root/.ssh/authorized_keys",),
                ):
            ctl.sendline(" ".join(cmd))
            i = ctl.expect(["[#] $", "[>] $", pexpect.TIMEOUT, pexpect.EOF,], timeout=TIMEOUT_SHORT)
            if i != 0:
                raise pexpect.ExceptionPexpect("command failed: %d" % i)

        return 0

    @classmethod
    def fromTrack(cls, switch):
        bt = TrackUtils.BigTrack()
        addr = bt.getSwitchV6Address(switch)
        if addr is None: return None
        intf = TrackUtils.getDefaultV6Intf()
        addr = addr + '%' + intf
        return cls(addr)
