#!/usr/bin/env python3
import json
from sys import exit, path
import argparse
import pickle as pkl
import fcntl
import copy
from automathemely import get_local

parser = argparse.ArgumentParser()
options = parser.add_mutually_exclusive_group()
options.add_argument('-l', '--list', help='list all current settings', action='store_true', default=False)
options.add_argument('-s', '--setting', help="change a specific setting (e.g. key.subkey=value)")
options.add_argument('-m', '--manage', help='easier to use settings manager GUI', action='store_true',
                     default=False)
options.add_argument('-u', '--update', help='updates the sunrise and sunset\'s crontabs manually', action='store_true',
                     default=False)


# For --setting arg
def lookup_dic(d, k):
    val = d
    for key in k:
        try:
            val = val[key]
        except KeyError:
            return False
    return True


# For --setting arg
def write_dic(dic, lis, val):
    if len(lis) == 0:
        return val
    else:
        key = lis.pop(0)
        dic[key] = write_dic(dic[key], lis, val)
    return dic


# For --list arg
def print_list(d, indent=0):
    for key, value in d.items():
        print('{}{}'.format('\t' * indent, key), end='')
        if isinstance(value, dict):
            print('.')
            print_list(value, indent + 1)
        else:
            print(' = {}'.format(value))


# ARGUMENTS FUNCTION
def main(us_se):
    args = parser.parse_args()
    if args.list:
        print('Current settings:')
        print_list(us_se)
        exit()

    elif args.setting:

        if not args.setting.count('=') == 1:
            exit('\nERROR: Invalid string (None or more than one "=" signs)')

        setts = args.setting.split('=')
        to_set_key = setts[0].strip()
        to_set_val = setts[1].strip()

        if to_set_key == '':
            exit('\nERROR: Invalid string (Empty key)')
        elif to_set_key[-1] == '.':
            exit('\nERROR: Invalid string (Key ends in dot)')
        if not to_set_val:
            exit('\nERROR: Invalid string (Empty value)')
        elif to_set_val.lower() in ['t', 'true', '1']:
            to_set_val = True
        elif to_set_val.lower() in ['f', 'false', '0']:
            to_set_val = False
        else:
            try:
                to_set_val = int(to_set_val)
            except ValueError:
                try:
                    to_set_val = float(to_set_val)
                except ValueError:
                    pass

        if to_set_key.count('.') > 0:
            key_list = [x.strip() for x in to_set_key.split('.')]
        else:
            key_list = [to_set_key]

        if lookup_dic(us_se, key_list):
            us_se = write_dic(us_se, key_list, to_set_val)

            with open(get_local('user_settings.json'), 'w') as file:
                json.dump(us_se, file, indent=4)

            # Warning if user disables auto by --setting
            if 'enabled' in to_set_key and not to_set_val:
                print('\nWARNING: Remember to set all the necessary values with either --settings or --manage')
            exit('Successfully set key "{}" as "{}"'.format(to_set_key, to_set_val))

        else:
            exit('\nERROR: Key "{}" not found'.format(to_set_key))

    # MANAGE
    elif args.manage:
        from . import settsmanager

        pid_file = '/tmp/automathemely_settings.pid'
        fp = open(pid_file, 'w')
        try:
            fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            return 'Another instance of the settings manager is already running!', True
        else:
            new_se = settsmanager.main(copy.deepcopy(us_se))

            # Dump file
            with open(get_local('user_settings.json'), 'w') as file:
                json.dump(new_se, file, indent=4)

            has_changed = (new_se != us_se)
            if has_changed:
                return 'Settings successfully saved', True
            else:
                return 'No changes were made', True

    # UPDATE
    elif args.update:
        from . import updsunhours
        output, is_error = updsunhours.main(us_se)
        if not is_error:
            with open(get_local('sun_hours.time'), 'wb') as file:
                pkl.dump(output, file, protocol=pkl.HIGHEST_PROTOCOL)
            return 'Sun hours successfully updated', True
        else:
            # Pass the error message for a notification popup
            return output, True