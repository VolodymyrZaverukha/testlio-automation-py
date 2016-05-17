from datetime import datetime, timedelta
from time import sleep
import pytz
import threading


local = threading.local()


def init(tcpdump_file_name='./dump.txt', host='pubads.g.doubleclick.net', time_zone_name='EST'):
    local.tcpdump_file_name = tcpdump_file_name
    local.host = host
    local.timezone = pytz.timezone(time_zone_name)


def validate(uri_contains=None, uri_not_contains=None, from_offset_in_seconds=60, to_offset_in_seconds=60, verbose=True):
    assert local.tcpdump_file_name and local.host and local.timezone, 'You need to initialise the tcp dump validator before using it. For that you need to call tcpdump.init()'
    assert uri_contains or uri_not_contains, 'uri_contains or uri_not_contains must be provided'

    datetime_validate_started = _get_datetime_now()
    datetime_from = datetime_validate_started - timedelta(seconds=from_offset_in_seconds)
    datetime_to = datetime_validate_started + timedelta(seconds=to_offset_in_seconds)

    # valid = None
    if uri_contains:
        valid = _validate_contains(uri_contains, datetime_from, datetime_to)
    else:
        valid = _validate_not_contains(uri_not_contains, datetime_from, datetime_to)

    if verbose:
        if valid:
            print('>> TCP dump validation succeded - uri_contains={0}, uri_not_contains={1}, methodCalledOn={2}, datetime_now={3}'.format(uri_contains, uri_not_contains, datetime_validate_started, _get_datetime_now()))
        else:
            print('>> TCP dump validation failed - uri_contains={0}, uri_not_contains={1}, methodCalledOn={2}, from_offset_in_seconds={3}, to_offset_in_seconds={4}'.format(uri_contains, uri_not_contains, datetime_validate_started, from_offset_in_seconds, to_offset_in_seconds))

    return valid


def _validate_contains(uri_contains, datetime_from, datetime_to):
    if not isinstance(uri_contains, list):
        uri_contains = [uri_contains]

    while _get_datetime_now() < datetime_to:
        tcpdump_lines = _read()
        for line in tcpdump_lines:
            if datetime_from < line['datetime'] < datetime_to and _all_present(line['path'], uri_contains):
                return True
        sleep(1)  # wait for one second before reading the file again

    return False


def _validate_not_contains(uri_not_contains, datetime_from, datetime_to):
    if not isinstance(uri_not_contains, list):
        uri_not_contains = [uri_not_contains]

    while _get_datetime_now() < datetime_to:
        tcpdump_lines = _read()
        for line in tcpdump_lines:
            if datetime_from < line['datetime'] < datetime_to and _any_present(line['path'], uri_not_contains):
                return False
        sleep(1)  # wait for one second before reading the file again

    return True


def _any_present(source_string, strings_to_find):
    if not strings_to_find or not source_string:
        return True

    return any(string_to_find in source_string for string_to_find in strings_to_find)


def _all_present(source_string, strings_to_find):
    if not strings_to_find:
        return True
    if not source_string:
        return False

    return all(string_to_find in source_string for string_to_find in strings_to_find)


def _read():
    with open(local.tcpdump_file_name, 'r') as tcpdump_file:
        file_content = []
        for line_string in tcpdump_file:
            parsed_line = _parse_line(line_string, local.host)
            if parsed_line:
                file_content.append(parsed_line)
        return file_content


def _parse_line(line_string, host_to_find=None):
    try:
        line = line_string.split(' ')

        host = line[5]
        if host != host_to_find:
            return

        return {
            'datetime': datetime.strptime(line[0] + line[1], '%Y-%m-%d%H:%M:%S'),
            'host': host,
            'path': line[8]
        }
    except:
        # print('Failed trying to parse line, skipping... [' + line_string + ']')
        return


def _get_datetime_now():
    datetime_now = datetime.now(local.timezone) + timedelta(hours=1)  # daylight savings time
    return datetime_now.replace(tzinfo=None)