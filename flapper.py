import argparse
import sys
import os
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
		if self.format is not None:
			fmt='--format "{0}"'.format(os.path.join(dest,self.format))

		if self.agent is not None:
			agt='--db "{0}"'.format(self.agent)

		if self.format is None:
			if self.agent is None:
				return ""
			else:
				return agt
		else:
			if self.agent is None:
				return fmt
			else:
				return "{0} {1}".format(fmt, agt)
			
	def __str__():
		self.build("")

	def __repr__():
		self.build("")
		
# Filebot wrapper
class FileBot:
	def __init__(self, binary):
		self.binary_path=binary
		self.order="airdate"
		self.strict=False
		self.anime=Format()
		self.movie=Format()
		self.tv=Format()
		self.destination="./"
		self.xattr=False
		self.filters=None
		self.strict=False

	def run(self, files, mode=Mode.TV, test=False, prompt=False, display=False):
		cmd=[self.binary_path]

		if self.xattr is False:
			cmd+=["-no-xattr"]

		if test is True:
			cmd+=["--action test"]
		else:
			cmd+=["--action move"]
			
		if mode is Mode.ANIME:
			cmd+=[self.anime.build(self.destination)]
		elif mode is Mode.MOVIE:
			cmd+=[self.movie.build(self.destination)]
		elif mode is Mode.TV:
			cmd+=[self.tv.build(self.destination)]
		elif mode is CLEANUP:
			pass
		elif mode is REVERT:
			pass

		for f in files:
			cmd+=['-rename "{0}"'.format(f)]

		print(cmd)
	
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
			    config=None)
	
	parser.add_argument('paths', metavar="PATH",  nargs="+", help="Files or directories to match.")
	
	modes_group = parser.add_argument_group("Modes", "Sets which type of matching is to be done. Only one should be used at a time, as they will override each other. Defaults to TV matching.")
	modes_group.add_argument("-a", 	"--anime",	action="store_const", 	dest="mode",	const=Mode.ANIME, 	help="Anime matching mode. This will first rename using absolute numbering, then match using season numbering.")
	modes_group.add_argument("-m",	"--movies", 	action="store_const", 	dest="mode",	const=Mode.MOVIE, 	help="Movie matching mode.")
	modes_group.add_argument(	"--tv", 	action="store_const", 	dest="mode",	const=Mode.TV,		help="TV matching mode.")
	modes_group.add_argument("-c",	"--cleanup", 	action="store_const", 	dest="mode", 	const=Mode.CLEANUP,	help="Cleanup mode.")
	modes_group.add_argument(	"--revert", 	action="store_const", 	dest="mode", 	const=Mode.REVERT,	help="Reverts changes made to file.")

	test_group = parser.add_argument_group("Dry Run", "Options for making dry runs. When any of these are set, no files will be modified.")
	test_group.add_argument("-t", "--test",		action="store_true",	dest="test",	help="Performs a test run, displaying the changes that would be made.")
	test_group.add_argument("-p", "--prompt", 	action="store_true", 	dest="prompt",	help="Make a test run then prompt the user to continue with matching. (Same as -tp).")

	filter_group = parser.add_argument_group("Filters", "These commands apply filters to Filebot. These commands may be used multiple times to apply multiple filters.")
	filter_group.add_argument("-f", "--filter", 	metavar="STRING", 	action="append",	dest="filters",		help="Applies the passed filter.")
	filter_group.add_argument("-n", "--name", 	metavar="STRING", 	action="append",	dest="names",		help="Applies a filter to match the show/movie name.")

	parser.add_argument("--config",		metavar="PATH",	action="store",		dest="config",		help="Use the passed config file. (default: %(default)s)")
	parser.add_argument("--dest",		metavar="PATH",	action="store",		dest="dest",		help="Specify the destination of renamed media. (default: %(default)s)")
	parser.add_argument("--display", 			action="store_true", 	dest="display", 	help="Displays filebot commands instead of running them.")
	parser.add_argument("--override",	 		action="store_true", 	dest="override",	help="Override any conflicts.")
	parser.add_argument("--strict", 			action="store_true", 	dest="strict", 		help="Strict Matching.")
	parser.add_argument("--non-strict", 			action="store_false", 	dest="strict", 		help="Non-strict matching. This is the default behaivor.")
	parser.add_argument("--xattr", 				action="store_true", 	dest="x-attr", 		help="Set extended attribuites.")
	
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
	filebot.destination=general_cfg.get("destination", "./")

	filebot.run(args.paths, mode=Mode.ANIME)
	filebot.run(args.paths, mode=Mode.MOVIE)
	filebot.run(args.paths, mode=Mode.TV)
	

# keep at bottom
if __name__ == "__main__":
	main()
