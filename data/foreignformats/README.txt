This directory holds examples of Managed Objects snapshots recorded by
other popular SNMP tools and stored in their own proprietary formats.

Snmpsim currently supports the following foreign data file formats:

* Net-SNMP's snmpwalk output (with -ObentU options)
* SimpleAgentPro sapwalk/sapwalk2

Please note that foreign formats do not allow for snmpsim's advanced features
such as dynamic value variation or triggering events to external systems.
If you possess a snapshot in a foreign format and wish to use advanced 
snmpsim's features, do "snmprec" against "snmpsim" serving foreign data file
to aqcuire a snapshot in snmpsim's native .snmprec form.

Since snmpsim does not tolerate comments in data files, make sure to remove
ones from .sapwalk prior to feeding them to snmpsim.
