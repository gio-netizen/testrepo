"""
:version 0.2
:author Miguel Dominguez
:email: miguel.a.dominguez@nokia.com
"""

import argparse
import logging
import sys

import pandas as pd
from vspk import v5_0 as vsdk


# Information about how to use it: https://nuagenetworks.github.io/vspkdoc/index.html
# Information about how to use the API calls: https://nuagenetworks.github.io/vsd-api-documentation/index.html

# INFO: The user and password for the VSD API are the default ones.
def start_session(ip: str, username: str = 'csproot', password: str = 'csproot'):
    """
    Initialize a session with the VSD API and returns a nuage user
    :param username:
    :param password:
    :param ip:
    :return session.user:
    """

    try:
        logging.info('Establishing connection to VSD API...')
        session = vsdk.NUVSDSession(username=username, password=password,
                                    enterprise='csp',
                                    api_url=f"https://{ip}:8443")
        session.start()
        logging.info('Connection established successfully!')
        return session.user
    except Exception as error:
        logging.error(f'Failed to connect to VSD API server.\n {error}\n')
        sys.exit(1)


def create_rate_limiter(name, description, committed_information_rate,
                        peak_information_rate, peak_burst_size,
                        enterprise=False):
    """
    Creation of a Rate Limiter
    Link: https://nuagenetworks.github.io/vspkdoc/v5_0/nunsgateway.html
    :param name:
    :param description:
    :param committed_information_rate:
    :param peak_information_rate:
    :param peak_burst_size:
    :param enterprise:
                An optional parameter or parameter set up with default values
                must be outlined at the end of the args list. We set up this
                argument as optional since we can go without of it
                if rate limiter creation is performed at Platform level.
    :return:
    """

    # Building the Rate Limiter object
    rl = vsdk.nuratelimiter.NURateLimiter(name=name,
                                          description=description,
                                          committed_information_rate=committed_information_rate,
                                          peak_information_rate=peak_information_rate,
                                          peak_burst_size=peak_burst_size)
    try:
        # If enterprise argument is not provided, rate limiter creation is
        # performed at platform level
        if enterprise == False:
            nuage_user.create_child(rl)
            logging.info(f'Rate limiter: {name} with: CIR: {committed_information_rate}, '
                         f'PIR: {peak_information_rate}, Burst Size: {peak_burst_size}; '
                         f'has been created successfully.')
        else:
            enterprise.create_child(rl)
            em = str(enterprise.name)
            logging.info(f'Enterprise: {em}, Rate limiter: {name}'
                         f' with: CIR: {committed_information_rate}, '
                         f'PIR: {peak_information_rate}, Burst Size: {peak_burst_size}; '
                         f'has been created successfully.')
    except Exception as error:
        logging.error(f'Failed to create {name} rate limiter. {error}')


def delete_rate_limiter(name, enterprise=False):
    """
    Deletion of a Rate Limiter
    :param name:
    :param enterprise:
            The same as the creation function. This argument is optional.
    :return:
    """

    # Fetching the rate limiter based on its name
    if enterprise == False:
        rl = nuage_user.rate_limiters.get_first(filter=f'name is "{name}"')
    else:
        rl = enterprise.rate_limiters.get_first(filter=f'name is "{name}"')

    try:
        rl.delete()
        if enterprise == False:
            logging.info(f'Rate limiter: {name}, deleted successfully!')
        else:
            logging.info(f'Enterprise: {enterprise.name}, Rate limiter: {name}, '
                         f'deleted successfully!')
    except Exception as error:
        logging.error(f'Failed to delete {name} rate limiter. {error}')


def find_by_name(name, array):
    for element in array:
        if element.name == name:
            return element
    return None


if __name__ == '__main__':
    # Checking if the required arguments are provided
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--api_address', type=str, required=True)
    parser.add_argument('-f', '--csv_file', type=str, required=True)
    parser.add_argument('-d', '--delete', action='store_true', required=False)
    parser.add_argument('-e', '--enterprise', action='store_true', required=False)
    ns = parser.parse_args()
    # Establishing session
    logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.INFO,
                        datefmt="%H:%M:%S")
    VSD_API_ADDRESS = ns.api_address
    nuage_user = start_session(VSD_API_ADDRESS)
    # Loading CSV file
    CSV_FILE = ns.csv_file
    logging.info('Reading the CSV file of the environment ...')
    data = pd.read_csv(CSV_FILE, encoding='latin1')

    # If -e argument is provided, the script performs Rate Limiters creation by
    # Enterprise, otherwise, creation is performed at Platform level
    if ns.enterprise == True:
        # Fetching all the enterprises registered on the VSD
        enterprises = nuage_user.enterprises.get()

        # If argument -d is provided, it activates delete function, otherwise,
        # create function is called
        if ns.delete == False:
            # Creation at Enterprise level
            for index, row in data.iterrows():
                enterprise = find_by_name(row['ORGANIZATION'], enterprises)
                create_rate_limiter(row['NAME'], row['DESCRIPTION'], row['CIR'],
                                    row['PIR'], row['BURST_SIZE'], enterprise)
        else:
            # Deletion at Enterprise level
            for index, row in data.iterrows():
                enterprise = find_by_name(row['ORGANIZATION'], enterprises)
                delete_rate_limiter(row['NAME'], enterprise)
    else:
        if ns.delete == False:
            # Creation at Platform level
            for index, row in data.iterrows():
                create_rate_limiter(row['NAME'], row['DESCRIPTION'], row['CIR'],
                                    row['PIR'], row['BURST_SIZE'])
        else:
            # Deletion at Platform level
            for index, row in data.iterrows():
                delete_rate_limiter(row['NAME'])