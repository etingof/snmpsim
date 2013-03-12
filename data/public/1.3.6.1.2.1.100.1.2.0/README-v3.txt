This directory serves as a special case only when Simulator is NOT running
in --v2c-arch mode.

This is a ContextName AND transport domain specific directory.

The .snmprec files in this directory would be used by Simulator whenever
ContextName in request AND transport domain AND source address being
used matches the .snmprec filename.

Since this is a IPv6 transport domain, .snmprec files take shape of
an IPv6 IP address with semicolons (:) replaces with underscores (_).
