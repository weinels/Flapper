import argparse
import sys
import os
import subprocess
import re
import shlex
import colorama
from colorama import Fore
from configparser import ConfigParser
from enum import Enum
from operator import attrgetter
from pathlib import Path

# enumeration of the modes
class Mode(Enum):
	ANIME=1
	MOVIE=2
	TV=3
	CLEANUP=4
	REVERT=5

# help formatter for the argument parser
class SortingHelpFormatter(argparse.HelpFormatter):
	def add_arguments(self, actions):
		actions = sorted(actions, key=attrgetter('dest'))
		super(SortingHelpFormatter, self).add_arguments(actions)

# format class
class Format:
	def __init__(self, format=None, agent=None):
		self.format = format
		self.agent = agent

	def build(self, dest):
		cmd = []
		if self.format is not None:
			cmd+=['--format',  '{0}'.format(os.path.join(dest,self.format))]

		if self.agent is not None:
			cmd+=['--db', '{0}'.format(self.agent)]

		return cmd
		
# Filebot wrapper
class FileBot:
	# pre-compiled regex objects
	move_regex = re.compile(r"\[(TEST|MOVE)\] Rename \[(.+)\] to \[(.+)\]")
	skip_regex = re.compile(r"Skipped \[(.+)\] because \[(.+)\] already exists")
	access_regex = re.compile(r"java.nio.file.AccessDeniedException: (.+)")
	revert_regex = re.compile(r"\[(TEST|MOVE)\] Revert \[(.+)\] to \[(.+)\]")
	clean_regex = re.compile(r"Delete (.+)")

	# constructor
	def __init__(self, binary):
		self.binary_path=binary
		self.order="airdate"
		self.strict=False
		self.anime=Format()
		self.movie=Format()
		self.tv=Format()
		self.xattr=False
		self.filters=None
		self.strict=False
		self.raw=False
		self.display=False

	# attempt to fix a filebot install
	def fix(self):
		# clear the cache, this usually fixes things
		cmd=[self.binary_path]
		cmd+=["-clear-cache"]
		subprocess.run(cmd, check=True)

	# primary way to invoke filebot
	def run(self, files, mode=Mode.TV, test=False, dest="./"):
		# the command to run will store in a list
		cmd=[self.binary_path]

		# check if we want to set extended attributes
		if self.xattr is False:
			cmd+=["-no-xattr"]

		# check if want non-strict matching
		if self.strict is not True:
			cmd+=["-non-strict"]

		# set the episode ordering we want to use
		if self.order is not None:
			cmd+=["--order", "{0}".format(self.order)]

		# set wether this is a dry run or not
		if test is True:
			cmd+=["--action", "test"]
		else:
			cmd+=["--action", "move"]

		# if the destination is the current directory, then leave it out to make the paths look nicer
		if dest == "./":
			dest = ""

		# any mode that has to invoke a Filebot script handles the filenames different
		if mode is Mode.CLEANUP:
			for f in files:
				cmd+=['-script', 'fn:cleaner', '{0}'.format(f)]
		elif mode is Mode.REVERT:
			for f in files:
				cmd+=['-script', 'fn:revert', '{0}'.format(f)]
		else:
			# use the appropriate format
			if mode is Mode.ANIME:
				cmd+=self.anime.build(dest)
			elif mode is Mode.MOVIE:
				cmd+=self.movie.build(dest)
			elif mode is Mode.TV:
				cmd+=self.tv.build(dest)

			# tell filebot to rename each file or directory
			for f in files:
				cmd+=['-rename', '{0}'.format(f)]

		# check to see if we need to display the command
		if self.display is True:		
			print(" ".join(cmd))
			return True

		# run the command
		try:
			p = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8")
		except subprocess.CalledProcessError as err:
			print("Filebot error:")
			if err.stdout is not None:
				print(err.stdout)
			if err.stderr is not None:
				print(err.stderr)
			return None
			
		# Make the output more readable
		files=[]
		for line in p.stdout.split("\n"):
			# if the use requested the raw output, print the line
			if self.raw is True:
				print(line)

			# perform all the regex matching
			match_move = self.move_regex.match(line)
			match_skip = self.skip_regex.match(line)
			match_access = self.access_regex.match(line)
			match_revert = self.revert_regex.match(line)
			match_clean = self.clean_regex.match(line)

			# line up the paths to make visual confirmation easier
			if match_move is not None:
				files+=[match_move.group(3)]
				if self.raw is not True:
					print("{2}{0}{4} Rename: {3}{1}{4}".format(match_move.group(1), match_move.group(2), Fore.CYAN, Fore.YELLOW, Fore.RESET))
					print("         To: {1}{0}{2}".format(match_move.group(3), Fore.GREEN, Fore.RESET))

			# line up the paths of skipped files
			if match_skip is not None:
				print("Skipped: {0}".format(match_skip.group(1)))
				print("Because: {0}".format(match_skip.group(2)))

			# line up the paths for reverted files
			if match_revert is not None:
				files+=[match_revert.group(3)]
				if self.raw is not True:
					print("{0} Revert: {1}".format(match_revert.group(1), match_revert.group(2)))
					print("         To: {0}".format(match_revert.group(3)))

			# check for permissions errors
			if match_access is not None:
				if self.raw is not True:
					print("Access denied: {0}".format(match_access.group(1)))

			# by default the cleaner script doesn't differentiate it's output for a dry run, so we will do so now
			if match_clean is not None:
				files+=[match_clean.group(1)]
				if self.raw is not True:
					if test is True:
						print("Will Delete: {0}".format(match_clean.group(1)))
					else:
						print("Deleted: {0}".format(match_clean.group(1)))

		# return a list of successfully processed files, or None if unsuccessful
		if not files:
			return None
		else:
			return files

# mimics the select function from bash
def selector(items, prompt):
	if not items:
		return ''
		
	def ok(reply, itemcount):
		try:
			n = int(reply)
			return 1 <= n <= itemcount
		except:
			return False
			
	reply = -1
	itemcount = len(items)

	while not ok(reply, itemcount):
		for indexitem in enumerate(items):
			print ("{0}) {1}".format(indexitem[0]+1, indexitem[1]))

		reply = input(prompt).strip()
		
	return items[int(reply)-1]
		
def main():
	# some default parameters
	config_file=os.path.expanduser("~/.config/flapper/config.cfg")
	
	# parse command line options
	parser = argparse.ArgumentParser(description="Filebot wrapper.", formatter_class=SortingHelpFormatter)

	# set default parameters
	parser.set_defaults(mode=Mode.TV,
			    test=False,
			    prompt=False,
			    dest=None,
			    filter=None,
			    name=None,
			    config=None,
			    raw=False,
			    display=False,
			    order="airdate",
			    fix=False)
	
	parser.add_argument('paths', metavar="PATH",  nargs="*", help="Files or directories to match.")
	
	modes_group = parser.add_argument_group("Modes", "Sets which type of matching is to be done. Only one should be used at a time, as they will override each other. Defaults to TV matching.")
	modes_group.add_argument("-a", 	"--anime",	action="store_const", 	dest="mode",	const=Mode.ANIME, 	help="Anime matching mode. This will first rename using absolute numbering, then match using season numbering.")
	modes_group.add_argument("-m",	"--movies", 	action="store_const", 	dest="mode",	const=Mode.MOVIE, 	help="Movie matching mode.")
	modes_group.add_argument(	"--tv", 	action="store_const", 	dest="mode",	const=Mode.TV,		help="TV matching mode.")
	modes_group.add_argument("-c",	"--cleanup", 	action="store_const", 	dest="mode", 	const=Mode.CLEANUP,	help="Cleanup mode.")
	modes_group.add_argument(	"--revert", 	action="store_const", 	dest="mode", 	const=Mode.REVERT,	help="Reverts changes made to file.")

	test_group = parser.add_argument_group("Dry Run", "Options for making dry runs. When any of these are set, no files will be modified.")
	test_group.add_argument("-t", "--test",		action="store_true",	dest="test",	help="Performs a test run, displaying the changes that would be made.")
	test_group.add_argument("-p", "--prompt", 	action="store_true", 	dest="prompt",	help="Make a test run then prompt the user to continue with matching. (Same as -tp).")

#	filter_group = parser.add_argument_group("Filters", "These commands apply filters to Filebot. These commands may be used multiple times to apply multiple filters.")
#	filter_group.add_argument("-f", "--filter", 	metavar="STRING", 	action="append",	dest="filters",		help="Applies the passed filter.")
#	filter_group.add_argument("-n", "--name", 	metavar="STRING", 	action="append",	dest="names",		help="Applies a filter to match the show/movie name.")

	order_group = parser.add_argument_group("Ordering", "Determines which ordering to use when matching. Airdate is the defualt.")
	order_group.add_argument("--dvd",		action="store_const",	dest="order",	const="dvd",		help="Use the DVD ordering.")
	order_group.add_argument("--airdate",		action="store_const",	dest="order",	const="airdate",	help="Use the airdate ordering.")
	order_group.add_argument("--absolute",		action="store_const",	dest="order",	const="absolute",	help="Use the absolute episode number ordering.")
	
#	parser.add_argument("--config",		metavar="PATH",	action="store",		dest="config",		help="Use the passed config file. (default: %(default)s)")
	parser.add_argument("--dest",		metavar="PATH",	action="store",		dest="dest",		help="Specify the destination of renamed media. (default: %(default)s)")
	parser.add_argument("--display", 			action="store_true", 	dest="display", 	help="Displays filebot commands instead of running them.")
#	parser.add_argument("--override",	 		action="store_true", 	dest="override",	help="Override any conflicts.")
	parser.add_argument("--strict", 			action="store_true", 	dest="strict", 		help="Strict Matching.")
	parser.add_argument("--non-strict", 			action="store_false", 	dest="strict", 		help="Non-strict matching. This is the default behaivor.")
	parser.add_argument("--raw",				action="store_true",	dest="raw",		help="Prints the raw output from Filebot.")
	parser.add_argument("--x-attr",				action="store_true", 	dest="x-attr", 		help="Set extended attribuites.")
	parser.add_argument("--fix",				action="store_true",	dest="fix",		help="Attempt to fix filbot if it's acting wonky.")
	
	args = parser.parse_args()

	# if a config file was passed, use that
	if args.config is not None:
		print("Support for custom config paths forthcoming.")
		sys.exit(1)
	else:
		p = Path(config_file)
		if not p.exists():
			print("config file not found, creating default version.")
			# make sure the directory exists
			if not p.parent.exists():
				p.parent.mkdir(parents=True)
			
			# write the new config file
			config = ConfigParser()
			config['ANIME']={"format": "{n} - [{absolute}] - {t}",
					 "agent": "anidb"}
			config['MOVIES']={"format": "{n} ({y})",
					  "agent": "TheMovieDB"}
			config['TV']={"format": "{n} - {s00e00} - {t}",
				      "agent": "TheTVDB"}
			config['GENERAL']={"filebot_binary": "/usr/bin/filebot",
					   "destination": "./"}

			with open(config_file, 'w') as configfile:
				config.write(configfile)
					   
	# parse the config file
	config = ConfigParser()
	config.read(config_file)

	# start up colorama
	colorama.init()
	
	# extract all groups, throwing an error if any were omitted
	try:
		tv_cfg=config['TV']
		movie_cfg=config['MOVIE']
		anime_cfg=config['ANIME']
		general_cfg=config['GENERAL']
	except KeyError as err:
		print("Malformed config file.\nMissing section: {0}".format(err))
		sys.exit(1)
	
	# build the Filebot wrapper
	filebot = FileBot(general_cfg.get("filebot_binary","/usr/bin/filebot"))
	filebot.anime=Format(anime_cfg.get("format", "{n} - [{absolute}] - {t}"), anime_cfg.get("agent", "anidb"))
	filebot.movie=Format(movie_cfg.get("format", "{n} ({y})"), movie_cfg.get("agent", "TheMovieDB"))
	filebot.tv=Format(tv_cfg.get("format", "{n} - {s00e00} - {t}"),tv_cfg.get("agent", "TheTVDB"))
	filebot.raw=args.raw
	filebot.display=args.display
	filebot.order=args.order

	if args.dest is None:
		dest=general_cfg.get("destination", "./")
	else:
		dest=args.dest

	# if we were asked to fix filebot, do so and exit
	if args.fix is True:
		filebot.fix()
		return

	# at this point, we need to process any passed paths, if there are none, exit
	if not args.paths:
		print("No files to process.")
		return

	# TODO: come up with a better way to handle prompts, something that doesn't duplicate so much code 
	
	# to match absolute numbered anime to season/episode numbering takes two steps
	# First, use anidb to get the airdate for each episode
	# Then, pass the renamed files through TheTVDB to get season/episode numbering
	if args.mode == Mode.ANIME:
		print("Anime matching")
		print("--------------")
		print("Part 1: Getting airdates.\n")
		if args.test is True or args.prompt is True:
			ret = filebot.run(args.paths, mode=Mode.ANIME, test=True,  dest="./")
			if ret is not None:
				if args.prompt is True:
					if selector(["Continue", "Stop"],"#? ") == "Stop":
						return
				else:
					return
			else:
				return

		rfiles = filebot.run(args.paths, mode=Mode.ANIME, test=False,  dest="./")
		if rfiles is not None:
			print("Part 2: Matching season/episode numbering.\n")
			if args.test is True or args.prompt is True:
				ret = filebot.run(rfiles, mode=Mode.TV, test=True,  dest=dest)
				if ret is not None:
					if args.prompt is True:
						res = selector(["Continue", "Revert", "Stop"],"#? ")
						if res == "Stop":
							return
						elif res == "Revert":
							filebot.run(rfiles, mode=Mode.REVERT, dest="./")
							return
					else:
						return
				else:
					return
			
			filebot.run(rfiles, mode=Mode.TV, test=False,  dest=dest)

	# all other matching just invokes filebot directly
	else:
		if args.test is True or args.prompt is True:
			ret = filebot.run(args.paths, mode=args.mode, test=True,  dest=dest)
			if ret is not None:
				if args.prompt is True:
					if selector(["Continue", "Stop"],"#? ") == "Stop":
						return
				else:
					return
			else:
				return

		filebot.run(args.paths, mode=args.mode, test=False,  dest=dest)

# keep at bottom
if __name__ == "__main__":
	main()
