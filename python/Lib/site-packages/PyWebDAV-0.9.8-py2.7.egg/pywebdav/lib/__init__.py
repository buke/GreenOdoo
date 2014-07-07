
import pkg_resources

# get version from package
package = pkg_resources.require('PyWebDAV')[0]
VERSION = package.version

# author hardcoded here
AUTHOR = 'Simon Pamies (spamsch@gmail.com)'
