#!/usr/bin/env python

import opscore.protocols.keys as keys
import opscore.protocols.types as types

class GingaCmd(object):
    def __init__(self, actor):
        # This lets us access the rest of the actor.
        self.actor = actor

        # Declare the commands we implement. When the actor is started
        # these are registered with the parser, which will call the
        # associated methods when matched. The callbacks will be
        # passed a single argument, the parsed and typed command.
        #
        self.vocab = [
            ('ping', '', self.ping),
            ('status', '', self.status)
        ]

        # Define typed command arguments for the above commands.
        self.keys = keys.KeysDictionary("ginga_ginga", (1, 1),
                                        keys.Key("text", types.String(), help=""),
                                        )

    def ping(self, cmd):
        cmd.finish('text="ok"')

    def status(self, cmd):
        self.actor.sendVersionKey(cmd)
        cmd.finish()

