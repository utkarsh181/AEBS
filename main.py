#!/bin/python
import csv
import os
import sys
import re
import subprocess
import argparse
import getpass

dotfiles = 'https://github.com/utkarsh181/dotfiles' # config files
aurhelper = 'yay' # AUR helper to ease installation from AUR
progsfile = 'progs.csv' # list of packages to be installed
user = '' # default username
pip_check = False # flag to check for python-pip package

# checks internet connection and distribution
def check_environment():
    try:
        check_pacman = ['pacman', '-Sy']
        subprocess.run(check_pacman, capture_output=True, check=True)
        return True
    # Filenotfounderror for Windows 10
    except (subprocess.CalledProcessError, FileNotFoundError) :
        return False

# parse cmd line args and sets global variable accordingly
def cmd_args():
    global dotfiles, aurhelper, progsfile
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--dotfiles', help='dotfiles repo '
                        '(local files or url)')
    parser.add_argument('-p', '--program', help='dependencies and'
                        ' program csv (local file or url)')
    parser.add_argument('-a', '--aur_helper', help='AUR helper '
                        '(must have pacman like syntax)')
    args = parser.parse_args()
    if args.dotfiles :
        dotfiles = args.dotfiles
    if args.program :
        progsfile = args.program
    if args.aur_helper :
        aurhelper = args.aur_helper

def error_message(msg):
    red = "\033[1;31m"
    reset = "\033[0;0m"
    sys.stdout.write(red)
    print('Error: ', end='')
    sys.stdout.write(reset)
    print(msg)

def warning_message(msg):
    orange = "\33[33m"
    reset = "\033[0;0m"
    sys.stdout.write(orange)
    print('Warning: ', end='')
    sys.stdout.write(reset)
    print(msg)

def green_msg(msg):
    green = "\33[32m"
    reset = "\033[0;0m"
    sys.stdout.write(green)
    print(msg)
    sys.stdout.write(reset)

def welcome_message():
    with open('welcome.txt', 'r') as f:
        msg = f.read()
        green_msg(msg)

# checks given user exist on system
def check_users():
    try:
        global user
        check_u = ['id', '-u', user]
        subprocess.run(check_u, capture_output=True, check=True)
        return False
    except subprocess.CalledProcessError :
        return True

# add repodir = directory to clone all repo's
def set_repodir(home):
    try:
        repodir = home + '/.local/src'
        mkdir = ['mkdir', '-p', repodir]
        subprocess.run(mkdir, capture_output=True)
        chown1 = ['chown', user+':wheel', home + '/.local']
        chown2 = ['chown', user+':wheel', repodir]
        subprocess.run(chown1, capture_output=True)
        subprocess.run(chown2, capture_output=True)
    except subprocess.CalledProcessError as error:
        error_message(error.stderr)

# add user account
def add_user():
    try:
        global user
        home = '/home/' + user
        useradd = ['useradd', '-m', '-g', 'wheel',
                   '-s', '/bin/zsh', user]
        subprocess.run(useradd, capture_output=True, check=True)
        set_repodir(home)
    # if users exist, then modify user account
    except subprocess.CalledProcessError:
        usermod = ['usermod', '-a', '-G', 'wheel', user]
        subprocess.run(usermod, capture_output=True, check=True)
        mkdir = ['mkdir', '-p', home]
        subprocess.run(mkdir)
        chown = ['chown', user+':wheel', home]
        subprocess.run(chown)
        set_repodir(home)

# add user's password
def add_pass(password):
        global user
        chpass= 'echo ' + user + ':' + password + ' | chpasswd'
        subprocess.run(chpass, shell=True)

def set_user_pass():
    global user

    print('Enter username: ', end='')
    user = input()
    while re.match('[a-z_][a-z0-9_-]*[$]?', user) == None:
        error_message('Username not valid.'
                      ' Give a username beginning with a letter, '
                      'with only lowercase letters, - or _.')
        print("Re-enter username: ", end='')
        user = input()
    pass1 = getpass.getpass('Enter password: ')
    pass2 = getpass.getpass('Re-enter password: ')
    while pass1 != pass2:
        try:
            error_message('Passwords do not match')
            pass2 = getpass.getpass('Re-enter password: ')
        except KeyboardInterrupt:
            print("At least type password correctly!")
            exit(1)
    if not check_users():
        warning_message("Given user already exist!!"
                        " If continued conflicting file will be overwritten.")
        print("Do you want to continue(yes/no)? :", end='')
        ques = input()
        if ques != 'yes':
            exit(1)
    add_user()
    add_pass(pass1)

def sudo_settings(text):
    sed = ['sed', '-i', '/#installer/d', '/etc/sudoers']
    subprocess.run(sed)
    with open('/etc/sudoers', 'a') as f:
        f.write(text)

# install 'aurhelper' using makepkg
def get_aurhelper():
    try:
        global aurhelper, user
        pwd = os.getcwd()
        print(f"Installing: {aurhelper}")
        os.chdir('/tmp')
        get_source = ['curl', '-sO', 'https://aur.archlinux.org/cgit/aur.git/snapshot/'+aurhelper+'.tar.gz']
        subprocess.run(get_source, capture_output=True, check=True)
        extract = ['sudo', '-u', user, 'tar', '-xvf', aurhelper+'.tar.gz']
        subprocess.run(extract, capture_output=True, check=True)
        os.chdir('/tmp/'+aurhelper)
        install = ['sudo', '-u', user, 'makepkg', '--noconfirm', '-si']
        subprocess.run(install, capture_output=True, check=True)
        # back to invocation directory
        os.chdir(pwd)
    except subprocess.CalledProcessError as error:
        error(error.stderr)

# install package from standard repository
def standard_install(package):
    try:
        pacman = ['pacman', '-S', '--noconfirm', '--needed', package]
        subprocess.run(pacman, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as error:
        error_message(error.stderr)
    except Exception as error:
        error_message(error)

# install package for AUR using 'aurhelper'
def aur_install(package):
    try:
        global user, aurhelper
        aur = ['sudo', '-u', user, aurhelper, '-S', '--noconfirm', package]
        subprocess.run(aur, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as error:
        error_message(error.stderr)
    except Exception as error:
        error_message(error)

# get code from git and compile it  using make
def gitmake_install(package):
    try:
        global user
        pwd = '/home/' + user + '/.local/src'
        os.chdir(pwd)
        make = ['make', 'install']
        bname = ['basename', package]
        get_repo_name = subprocess.run(bname, capture_output=True, text=True)
        repo_name = get_repo_name.stdout
        repo_name = repo_name.splitlines()[0] # remove trailing '\n'
        install_dir = pwd + '/' + repo_name
        git_clone = ['sudo', '-u', user, 'git', 'clone', package]
        subprocess.run(git_clone, capture_output=True, check=True)
        os.chdir(install_dir)
        subprocess.run(make, capture_output=True)
        os.chdir('/tmp')
    # if git clone fails that pull from master branch
    except subprocess.CalledProcessError as error:
        os.chdir(install_dir)
        git_pull = ['sudo', '-u', user, 'git', 'pull' ,
                    '--force', 'origin', 'master']
        subprocess.run(git_pull, capture_output=True)
        subprocess.run(make, capture_output=True)
        os.chdir('/tmp')
    except Exception as error:
        error_message(error)

# install package from pip
def pip_install(package):
    try:
        global pip_check
        if pip_check == False:
            standard_install('python-pip')
            pip_check = True
        pip = ['pip', 'install', package]
        subprocess.run(pip, capture_output=True, check=True)
    except subprocess.CalledProcessError as error:
        error_message(error.stderr)

def install_prog():
    global user, progsfile
    # TODO: use curl to install if url is provided
    with open(progsfile, 'r', newline='') as csvfile:
        tag_name = ['tag', 'name', 'purpose']
        prog_csv = csv.DictReader(csvfile, fieldnames=tag_name)
        next(prog_csv) # to skip first line of csv file
        for row in prog_csv:
            print(f"Installing: {row['name']}")
            if row['tag'] == 'G':
                gitmake_install(row['name'])
            elif row['tag'] == 'A':
                aur_install(row['name'])
            elif row['tag'] == 'P':
                pip_install(row['name'])
            else :
                standard_install(row['name'])

def put_dotfiles():
    try:
        global dotfiles
        global user
        os.chdir('/tmp')
        git_clone = ['sudo', '-u', user, 'git', 'clone', dotfiles]
        subprocess.run(git_clone, capture_output=True, check=True)
        bname = ['basename', dotfiles]
        get_repo_name = subprocess.run(bname, capture_output=True, text=True)
        repo_name = get_repo_name.stdout
        repo_name = repo_name.splitlines()[0] # remove trailing '\n'
        dot_dir = '/tmp/' + repo_name
        copy = ['sudo', '-u', user, 'cp', '-rfT', dot_dir, '/home/'+user]
        subprocess.run(copy, capture_output=True, check= True)
    except subprocess.CalledProcessError as error:
        error_message(error.stderr)

def systembeep_off():
    rm = ['rmmod', 'pcspkr']
    subprocess.run(rm)
    beepconf = 'echo "blacklist pcspkr" > /etc/modprobe.d/nobeep.conf'
    subprocess.run(beepconf, shell=True)

def finalize():
    green_msg('Congrats! Provided there were no hidden errors,'
              ' the script completed successfully and '
              'all the programs and configuration files should be in place.')

if __name__ == "__main__":
    cmd_args()
    # TODO: add some notification
    if check_environment():
        green_msg("Environment check passed!!")
    else:
        error_message("Are you sure you're running this as the root user,"
                      " are on an Arch-based distribution and "
                      "have an internet connection?")
        exit(1)
    welcome_message()
    set_user_pass()
    # Allow user to run sudo without password. Since AUR programs must be installed
    # in a fakeroot environment, this is required for all builds with AUR.
    sudo_settings("%wheel ALL=(ALL) NOPASSWD: ALL #installer\n")
    # get_aurhelper()
    # install_prog()
    # put_dotfiles()
    systembeep_off()
    # This line, overwriting the `sudo_settings()` above will allow the user to runp
    # serveral important commands, `shutdown`, `reboot`, updating, etc. without a password.
    sudo_settings("%wheel ALL=(ALL) ALL #installer\n%wheel ALL=(ALL) NOPASSWD: "
                  "/usr/bin/shutdown,/usr/bin/reboot,/usr/bin/systemctl suspend,"
                  "/usr/bin/wifi-menu,/usr/bin/mount,"
                  "/usr/bin/umount,/usr/bin/pacman -Syu,/usr/bin/pacman -Syyu,"
                  "/usr/bin/packer -Syu,/usr/bin/packer -Syyu,"
                  "/usr/bin/systemctl restart NetworkManager,"
                  "/usr/bin/rc-service NetworkManager restart,"
                  "/usr/bin/pacman -Syyu --noconfirm,/usr/bin/loadkeys,"
                  "/usr/bin/yay,/usr/bin/pacman -Syyuw --noconfirm #installer\n")
    finalize()
