# Steamer #
Steamer is a Flask app that allows you to download games overnight on slow connections utilizing an external server rather than your main PC (though, you can still use your main PC with it).

This project is probably dead due to changes in the Python steam library (which hasn't been updated in a year) and the code just straight up no longer logging you in.

Like, it doesn't work and I'm tired of trying to make it work. Who knows.

## Why? ##
This application exists for several reasons:

- I wanted a way to download games at night that did not require my PC being on, and I had a Raspberry Pi kicking around
- The official headless steam client [SteamCMD](https://developer.valvesoftware.com/wiki/SteamCMD) is restricted to x86 and x86_64 machines; nothing official exists for ARM devices (like a Raspberry Pi)
- I wanted a project. Sue me.

## Installation ##
### Prerequisites ###
`Python>=3.5`. I don't have an exact version required, so you may be able to get away with less. Just not Python 2.

The steam client emulator we are using requires [Gevent](https://www.gevent.org/install.html), so be sure you have whatever it requires. For the RPI4, it requires binaries for `make`, `gcc`, and probably `cc`. If you run into issues when you're installing pip packages, this is probably why.

### Process ###

First, clone the repository and enter the directory

```bash
git clone https://github.com/Caddox/Steamer.git
cd Steamer
```

Next, install the required packages using Pip, making a venv if you prefer.
```bash
python -m pip install -r requirements.txt
```

Finally, you can run the server normally with Flask:
```bash
# The --host=0.0.0.0 part allows other computers on LAN to see the server.
# This is not required if you are running the server on localhost.
python -m flask run --host=0.0.0.0
```

With another computer on your local network, you can then access it by visiting the IP in your browser at port *5000*
```bash
# If you ran with --host=0.0.0.0
xxx.xxx.xxx.xxx:5000 # Your IP will be different; check the log file for what it will be for you.

# Otherwise
localhost:5000
```

You will then be prompted to log into your Steam Account.

## Settings ##
The settings page includes a download path, and filters for OS and Languages. By default, the download path with resolve to `Steamer/.downloads/`, the language will be set to English, and the valid OS's will be set to Windows. 

Adding a language or OS to the filters will mark it for downloading when you go to download a game, so be sure to include the ones you want!

Be sure to setup the download path to wherever you want -- like an external hard drive with the space you need.

## FAQ ## 
**You seem to have a pretty specific use case; why should I do it your way?**

You don't have to; this is just another option available to you. There are many different tools built for Steam, such as Bot Traders, local Steam Caching servers, and even tools to idle in games for Steam Trading Cards. The closest thing to this is probably [steamctl](https://github.com/ValvePython/steamctl), which is another option if you like using the command line for everything. (Fun fact: Steamer started life as a wrapper for steamctl!)

#

**The timestamp in the log file and the actual time is compleatly different! Why?**

Python's `time` module accesses the time given by the Operating System. If you are running a Raspberry Pi or another flavor of Linux, be sure to set your Timezone correctly. Otherwise, the program will operate off of GMT, which (unless you live in the Greenwich Mean Time zone) is probably not what you want. (Hint: on Linux, look up `timedatectl`)

#

**I've finished downloading a game, but it's on my server, not my computer! I can't game with it there!**

Yep, you've gotta move the game files to a Steam install directory for them to work. You can copy files over the network with something like [WinSCP](https://winscp.net/); or, if you downloaded the games to an external hard drive, walk the ten steps to the next room and bring the hard drive back, then copy the files.

#

**How do I get Steam itself to recognize the game files?**

First, exit Steam. Copy the game files from the server into wherever your `SteamApps/common` folder is. Then, start Steam and attempt to download the game. Steam should notice you have existing files for the game, and will verify them. If you've done everything correct, Steam will verify the files and then notify you that it's done downloading without downloading anything at all.

#

**I copied the files like you said, but Steam still wants to download something. What did I do wrong?**

Probably nothing. There are some files Steam will sometimes re-download when going through the process of verifying the files (mostly *.exe files). Luckily, the assets of the game are often much larger than the *.exe itself. Additionally, the game may have updated since you downloaded it with Steamer, requiring Steam itself to update the game. 

#

**I noticed that a game I downloaded using Steamer and the same game I already had on my PC are different sizes. What's up with that?**

Steamer will try to only download depots that meet your settings, but sometimes naughty game developers do not set a config in their depot. If a depot is encountered that does not have a language or target OS defined, it will default to being downloading.

Normally, this isn't an issue. Sometimes, it is.

Another potential reason: during testing, I noticed that interrupting the download and restarting it caused some files to balloon in size. I believe this has something to do with append mode. I will get a better look at this eventually.

#

**Can I use Steamer to update my games?**

Theoretically, sure. It was not built with this in mind, however, so let me know if something goes wrong.

#


**Why are there so many games that I don't own showing up?**

Steamer lists all the *apps* you own, not just games. This means that some rather odd things get included that may not show up normally on Steam. Technically, you still own those items. Feel free to ignore them.

#

**Man, this CSS and website design is ugly! Why is it so bad?**

I am not a visual designer. I write code, and this was really my first attempt at writing something with HTML and CSS. If you'd like, you can make it better by contributing!
