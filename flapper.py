import argparse
import sys
import os
import subprocess
import re
import shlex
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
		if format is None:
			self.format = None
		else:
			self.format = format#.replace("'","\\'").replace("`","\\`").replace('"','\\"')
		self.agent = agent

	def build(self, dest):
		cmd = []
		if self.format is not None:
			cmd+=['--format "{0}"'.format(os.path.join(dest,self.format))]

		if self.agent is not None:
			cmd+=['--db "{0}"'.format(self.agent)]

		return cmd
		
# Filebot wrapper
class FileBot:
	# pre-compiled regex objects
	move_regex = re.compile(r"\[(TEST|MOVE)\] Rename \[(.+)\] to \[(.+)\]")
	skip_regex = re.compile(r"Skipped \[(.+)\] because \[(.+)\] already exists")
	access_regex = re.compile(r"java.nio.file.AccessDeniedException: (.+)")
	revert_regex = re.compile(r"\[(TEST|MOVE)\] Revert \[(.+)\] to \[(.+)\]")
	
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

	def fix(self):
		cmd=[self.binary_path]
		cmd+=["-clear-cache"]
		
		subprocess.run(cmd, check=True)
		
	def run(self, files, mode=Mode.TV, test=False, dest="./"):
		cmd=[self.binary_path]

		if self.xattr is False:
			cmd+=["-no-xattr"]

		if self.strict is not True:
			cmd+=["-non-strict"]

		if self.order is not None:
			cmd+=["--order", "{0}".format(self.order)]

		if test is True:
			cmd+=["--action", "test"]
		else:
			cmd+=["--action", "move"]

		if dest == "./":
			dest = ""

		if mode is Mode.CLEANUP or mode is Mode.REVERT:
			if mode is Mode.CLEANUP:
				pass
			elif mode is Mode.REVERT:
				for f in files:
					cmd+=['-script", "fn:revert", {0}'.format(f)]
		else:
			if mode is Mode.ANIME:
				cmd+=self.anime.build(dest)
			elif mode is Mode.MOVIE:
				cmd+=self.movie.build(dest)
			elif mode is Mode.TV:
				cmd+=self.tv.build(dest)
			for f in files:
				cmd+=['-rename', '{0}'.format(f)]

		# check to see if we need to display the command
		if self.display is True:		
			print(" ".join(cmd))
			return True

		# run the command
		files=[]
		p = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, encoding="utf-8")

		for line in p.stdout.split("\n"):
		#	line = byte_line.decode("utf-8")[:-1]

			if self.raw is True:
				print(line)
			
			match_move = self.move_regex.match(line)
			match_skip = self.skip_regex.match(line)
			match_access = self.access_regex.match(line)
			match_revert = self.revert_regex.match(line)
			
			if match_move is not None:
				files+=[match_move.group(3)]
				if self.raw is not True:
					print("{0} From: {1}".format(match_move.group(1), match_move.group(2)))
					print("     To:   {0}".format(match_move.group(3)))

			if match_skip is not None:
				print("Skipped: {0}".format(match_skip.group(1)))
				print("Because: {0}".format(match_skip.group(2)))

			if match_revert is not None:
				files+=[match_revert.group(3)]
				if self.raw is not True:
					print("{0} Revert: {1}".format(match_revert.group(1), match_revert.group(2)))
					print("         To: {0}".format(match_revert.group(3)))

			if match_access is not None:
				if self.raw is not True:
					print("Access denied: {0}".format(match_access.group(1)))
				
		print("")

		if len(files) == 0:
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

	parser.set_defaults(mode=Mode.TV,
			    test=False,
			    prompt=False,
			    dest="./",
			    filter=None,
			    name=None,
			    config=None,
			    raw=False,
			    display=False,
			    order="airdate",
			    fix=False)
	
	parser.add_argument('paths', metavar="PATH",  nargs="+", help="Files or directories to match.")
	
	modes_group = parser.add_argument_group("Modes", "Sets which type of matching is to be done. Only one should be used at a time, as they will override each other. Defaults to TV matching.")
	modes_group.add_argument("-a", 	"--anime",	action="store_const", 	dest="mode",	const=Mode.ANIME, 	help="Anime matching mode. This will first rename using absolute numbering, then match using season numbering.")
	modes_group.add_argument("-m",	"--movies", 	action="store_const", 	dest="mode",	const=Mode.MOVIE, 	help="Movie matching mode.")
	modes_group.add_argument(	"--tv", 	action="store_const", 	dest="mode",	const=Mode.TV,		help="TV matching mode.")
#	modes_group.add_argument("-c",	"--cleanup", 	action="store_const", 	dest="mode", 	const=Mode.CLEANUP,	help="Cleanup mode.")
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

	dest=general_cfg.get("destination", "./")

	if args.fix is True:
		filebot.fix()
		sys.exit()
	
	# run filebot
	if args.mode == Mode.ANIME:
		print("Anime matching")
		print("--------------")
		print("Part 1: Getting airdates for videos.\n")
		rfiles = fullrun(filebot, files=args.paths, mode=Mode.ANIME, test=args.test, prompt=args.prompt, dest="./")
		if rfiles is not None:
			print("Part 2: Matching videos using season/episode numbering.\n")
			if fullrun(filebot, files=rfiles, mode=Mode.TV, test=args.test, prompt=args.prompt, dest=dest) is None:
				print("")
				if selector(["Yes", "No"], "Revert Files? ") == "Yes":
					fullrun(filebot, files=rfiles, mode=Mode.REVERT, dest="./")				
			
	else:
		fullrun(filebot, files=args.paths, mode=args.mode, test=args.test, prompt=args.prompt, dest=dest)

# run filebot, performing a test run if needed and providing a prompt is needed
def fullrun(filebot, files, mode, test=False,prompt=False,  dest="./"):
	if test is True or prompt is True:
		ret = filebot.run(files, mode=mode, test=True,  dest=dest)
		if ret is not None:
			if prompt is True:
				if selector(["Continue", "Stop"],"#? ") == "Stop":
					return None
			else:
				return None
		else:
			return None

	return filebot.run(files, mode=mode, test=False,  dest=dest)
	

# keep at bottom
if __name__ == "__main__":
	main()
