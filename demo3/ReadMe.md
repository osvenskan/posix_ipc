These scripts demonstrate four message queue notification techniques.

All of demos ask you to enter a message. That message is then sent to the
queue and received in a notification handler and printed to stdout.

- one_shot_signal.py and one_shot_thread.py receive their notifications via a 
signal and thread, respectively. After one message & notification, the demo 
exits.

- repeating_signal.py and repeating_thread.py are similar, except that they
re-register for notifications in their notification handler so you can
enter as many messages as you like.
