### Seguro Fwd

This makes use of telethon to login in users

The log in process is done via the ADMIN panel

YOU WILL BE NEEDING Python 3.11.10 because higher versions doesn't support AIOHTTP

# Admin

The admin panel handles logging the client, managing the groups they are in by
toggling the groups to activate a group which the telegram ID is going to be logged
to the database.

The admin panel also manages turning off/on of the forwarder.

# forwarder folder
This is where the forwarding logic is...
It captures CA, pump.fun, dexscreener links from source groups and forwards them.
-  this should be modified as well.
-  specific group should be an excemption.

You can fork and push to a branch. 
Ty for assist. 
