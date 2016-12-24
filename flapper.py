import argparse
import sys
from enum import Enum
from operator import attrgetter

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
	
def main():
	# parse command line options
	
	parser = argparse.ArgumentParser(description="Filebot wrapper.", formatter_class=SortingHelpFormatter)

	parser.set_defaults(mode=Mode.TV,
			    test=False,
			    prompt=False,
			    dest="./",
			    filter="",
			    name="",
			    config="~/.config/flapper/config.cfg")
	
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
	parser.add_argument("--xattr", 			action="store_true", 	dest="x-attr", 		help="Set extended attribuites.")
	
	args = parser.parse_args()
# keep at bottom
if __name__ == "__main__":
	main()
