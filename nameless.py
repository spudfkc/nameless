#!/usr/bin/env python

import urllib2, json, sys, os, imp
import reviewer.Docker as docker

from reviewer import util
from reviewer.Gerrit import Gerrit
from shutil import rmtree

##############################################################################
### GLOBALS
##############################################################################

config = None
CONFIG_FILE = 'conf/nameless.config'

##############################################################################

# def checkoutChange(localProject, selectedChange, currentRev):
#     '''
#     A function that does too much.
#     '''
#     project = selectedChange.get('project')
#     gitUrl = selectedChange['revisions'][currentRev]['fetch']['ssh']['url']
#     gitRef = selectedChange['revisions'][currentRev]['fetch']['ssh']['ref']
#
#     # FIXME no hardcoded index, should be after protocol
#     urlParts = [gitUrl[:6], config['username'], '@', gitUrl[6:]]
#
#     gitUrl = ''.join(urlParts)
#
#     localProject = None
#     localProject = config.get('repos').get(project)
#     if localProject is None:
#         raise Exception('Unable to find project %s in config!' % project)
#     print('INFO: project is ' + str(localProject))
#
#     projectDir = ''.join([config.get('workspace'), '/', localProject])
#
#     git = Git(projectDir)
#     builder = UCDBuilder(projectDir)
#
#     originalbranch = git.current_branch()
#
#     git.fetch(gitUrl, gitRef)
#
#     git.checkout('FETCH_HEAD')
#     newbranch = selectedChange.get('change_id') + '/' + util.randstring(8)
#     git.new_branch(newbranch)
#
#     ucdDir = projectDir
#     ucdBuilder = builder
#     ucdGit = None
#     if project != 'urban-deploy':
#         ucdDir = ''.join([config.get('workspace'), '/',
#             config.get('repos').get('urban-deploy')])
#         ucdBuilder = UCDBuilder(ucdDir)
#         builder.publish()
#
#     # Build UCD
#     ucdBuilder.pre_build()
#     ucdBuilder.build()
#     ucdBuilder.post_build()
#
#     # restore original branch
#     git.checkout(originalbranch)
#
#     # cleanup the branch we made
#     git.delete_branch(newbranch)


# def displayReviews(reviews):
#     '''
#     Displays the given reviews in the terminal.
#
#     Each review is indexed, starting at 1.
#
#     Format:
#     (i) subject owner
#     '''
#     for i, review in enumerate(reviews):
#         line = [' (', str(i+1), ') ', review.get('subject'), '-',
#                 review.get('owner').get('name')]
#         print(' '.join(line))


# def getChange(reviews):
#     '''
#     Prompts the user to select a change to review given a list of reviews
#     This returns the selected change.
#     '''
#     selected = False
#     changeindex = -1
#     while not selected:
#         try:
#             changeindex = int(raw_input())
#             if changeindex > 0 and changeindex <= len(reviews):
#                 changeindex -= 1
#                 selected = True
#         except ValueError:
#             pass # ignore non-numeric input
#     return reviews[changeindex]


def display_help():
    # TODO update help message
    print(
        '''
        Usage: reviewer.py [-d] [-D]

            -d|--daemon           Starts the Docker container as a daemon.
            -D|--deploy-only      Skips any Gerrit/Git operations and deploys
                                  your current UCD directory to a container.
            -h|--help             Displays this text.
        ''')

def main():
    # parse arguments
    onlyDeploy = False
    daemonMode = False
    doBuild = True
    project = None
    if len(sys.argv) > 0:
        if '-D' in sys.argv or '--deploy-only' in sys.argv:
            onlyDeploy = True
        if '-d' in sys.argv or '--daemon' in sys.argv:
            daemonMode = True
        if '--no-build' in sys.argv:
            doBuild = False
        # TODO add project option
        if '-h' in sys.argv or '--help' in sys.argv:
            display_help()
            return

    # load config
    global config
    config = util.loadConfigFile(CONFIG_FILE)


    if onlyDeploy:
        project = config.get('default-project')
    else:
        # TODO gerrit stuff
        pass

    # get project builder and docker
    projectdir = ''.join([config.get('workspace'), '/', config.get('repos').get(project)])

    # build the project
    if doBuild:
        buildername = config.get('default-builder')
        buildermod = imp.load_source(buildername, ''.join(['./reviewer/plugins/', buildername, '.py']))
        builder = buildermod.load(projectdir)

        builder.prebuild()
        builder.build()
        builder.postbuild()

    # build a new docker image with our Dockerfile
    imageid = docker.build()

    # start up the new docker image
    cmd = ['run']
    if daemonMode:
        cmd = ['start']
    docker.run(imageid, cmd=cmd, daemon=daemonMode)

    print "done"
    exit(0)

#### GERRIT STUFF

    gerrit = Gerrit(config.get('gerrit-url'), config.get('gerrit-username'),
        config.get('gerrit-api-password'))

    reviews = gerrit.get_open_reviews()
    if len(reviews < 1):
        print('Found no open reviews')
        return 0

    display_reviews(reviews)
    selectedchange = get_change(reviews)

    project = selectedchange.get('project')
    # TODO get project-specific builder/docker

    currentrev = selectedchange.get('current_revision')

    try:
        localproject = config.get('repos').get('project')
    except KeyError:
        print('[ERROR] Could not find project %s in config' % project)
        return 1

    print('[INFO] project is %s' % project)

    checkout_change(localproject, selectedchange, currentrev)


   # if not onlyDeploy:
   #     gerrit = Gerrit(config.get('baseUrl'), config.get('username'),
   #         config.get('apiPasswd'))
   #     reviews = gerrit.get_open_reviews()
   #     if not len(reviews) > 0:
   #         print('No open reviews')
   #         exit(0)
   #     displayReviews(reviews)
   #      selectedChange = getChange(reviews)
   #
   #      project = selectedChange.get('project')
   #      currentRev = selectedChange.get('current_revision')
   #
   #      try:
   #          localProject = config.get('repos').get('project')
   #      except KeyError:
   #          print('ERROR: could not find project %s in config file' % project)
   #          exit(1)
   #
   #      print('INFO: project is %s' % project)
   #
   #      checkoutChange(localProject, selectedChange, currentRev)
   #
   #  docker = UCDDocker(''.join([config.get('workspace'), '/',
   #      config.get('repos').get('urban-deploy')]))
   #  docker.pre_build()
   #  image = docker.build(DOCKERFILE_DIR)
   #  runprocess = docker.run(image, daemon=daemonMode)
   #  if daemonMode:
   #      for mapping in docker.get_mapped_ports():
   #          print(mapping)

    print('done.')


##############################################################################


if __name__ == '__main__':
    main()