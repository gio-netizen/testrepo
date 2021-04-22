"""
:version 0.1
:author Luis Tapia
:email: luis.e.hernandez@nokia.com
"""

import argparse
import logging
import sys
import time
import ipaddress

import pandas as pd
from vspk import v5_0 as vsdk


def find_by_name(name, array):
    """
    TODO: write a description
    :param name:
    :param array:
    :return:
    """
    for element in array:
        if element.name == name:
            return element
    return None


def replace_many(original: str, substring_list: list, new: str) -> str:
    """
    TODO: write a description
    :param original:
    :param substring_list:
    :param new:
    :return:
    """
    # traverse the substring list to replace
    for string in substring_list:
        # test if string exists in the original string
        if string in original:
            # replace the string
            original = original.replace(string, new)
    return original


def start_session(ip: str, username: str = 'csproot', password: str = 'csproot'):
    """
    Initialize a session with the VSD API (VSP) and returns a nuage user
    :param username:
    :param password:
    :param ip:
    :return session.user:
    """
    try:
        session = vsdk.NUVSDSession(username=username, password=password, enterprise='csp',
                                    api_url=f"https://{ip}:8443")
        session.start()
        return session.user
    except Exception as error:
        logging.error(
            f'Failed to connect with VSD API server.\n {error}\n')
        sys.exit(1)


def create_subnet(subnet_zone, zone_name, domain_name, subnet_name, subnet_address, subnet_netmask, gateway):
    """
    Create a NUSubnet associated with a Zone.
    Link: https://nuagenetworks.github.io/vspkdoc/v6/nusubnet.html#nusubnet
    :param subnet_name:
    :param subnet_zone:
    :param subnet_address:
    :param subnet_netmask:
    :return: subnet
    """
    try:
        # REQUEST
        subnet = vsdk.nusubnet.NUSubnet(
            name=subnet_name, address=subnet_address, netmask=subnet_netmask, gateway=gateway)
        subnet_zone.create_child(subnet)

        # LOG
        logging.info(
            f'Subnet: {enterprise.name} > {zone_name} > {domain_name} > {subnet_name} has been created successfully.')
        return subnet
    except Exception as error:
        logging.error(
            f'The subnet {subnet_name} could not be created. {error}')


def address_range_subnet(subnet, min_address, max_address):
    """
    Address ranges are used for dynamic IP address within subnet.
    Link: https://nuagenetworks.github.io/vspkdoc/v6/nuaddressrange.html#nuaddressrange
    :param subnet:
    :param min_address:
    :param max_address:
    :return: address range
    """
    try:
        # REQUEST
        address_range = vsdk.nuaddressrange.NUAddressRange(
            dhcp_pool_type='BRIDGE', min_address=min_address, max_address=max_address)
        subnet.create_child(address_range)

        # LOG
        logging.info(
            f'Range {min_address} - {max_address} has been created successfully.')
        return address_range
    except Exception as error:
        logging.error(
            f'The range {min_address} - {max_address} could not be created. {error}')


def hex_encode(route):
    return b"".join([b"%02x" % octet for octet in route])


def dns_to_subnet(subnet, subnet_dns1, subnet_dns2):
    """
    Add DNS to the subnet
    Link: http://nuagenetworks.github.io/vspkdoc/v5_0/nudhcpoption.html
    :param subnet:
    :return:
    """
    try:
        data = [int(subnet_dns1.split('/')[1]), subnet_dns1.split('/')
                [0], subnet_dns2.split('/')[0]]
        dhcp_option = vsdk.nudhcpoption.NUDHCPOption(
            type='0x06', value=hex_encode(data))
        subnet.create_child(dhcp_option)
        logging.info(
            f'DNS {dhcp_option} has been created successfully.')
    except Exception as error:
        logging.info(
            f'DNS could not be created. {error}')


def delete_subnet(user, subnet_name, zone):
    """
    Add DNS to the subnet
    Link: https://nuagenetworks.github.io/vspkdoc/v6/nudhcpoption.html
    :param user:
    :param subnet:
    :param zone:
    :return:
    """
    try:
        subnet = zone.subnets.get_first(filter=f"name is '{subnet_name}'")
        subnet.delete()

        logging.info(
            f'Subnet {subnet_name} has been deleted successfully.')
    except Exception as error:
        logging.error(
            f'Subnet {subnet_name} does not exist {error}')


if __name__ == '__main__':
    # check if the arguments are provided
    # INFO: The user and password for the VSD API are the default ones.
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--api_address', type=str, required=True)
    parser.add_argument('-f', '--csv_file', type=str, required=True)
    ns = parser.parse_args()
    VSD_API_ADDRESS = ns.api_address
    CSV_FILE = ns.csv_file

    logging.basicConfig(format="%(asctime)s: %(message)s",
                        level=logging.INFO, datefmt="%H:%M:%S")

    logging.info('Starting the connection to the VSD API ...')
    nuage_user = start_session(VSD_API_ADDRESS)

    logging.info('Reading the CSV file of the environment ...')
    data = pd.read_csv(CSV_FILE, encoding='latin1')

    enterprises = nuage_user.enterprises.get()
    domains = nuage_user.domains.get()
    zones = nuage_user.zones.get()

    # COLUMNS NEEDS THIS FORMAT NAME
    # ORGANIZATION  = Enterprise / static
    # LAN1-VLAN1_DOMAIN  = Domain / dinamic
    # LAN1-VLAN1_ZONE  = Zone / dinamic
    # LAN1-VLAN1_SUBNET_NAME  = Subnet name / dinamic
    # LAN1-VLAN1_SUBNET = Mask / dinamic
    # LAN1-VLAN1_SUBNET_DNS1 = DNS1 / dinamic
    # LAN1-VLAN1_SUBNET_DNS2 = DNS2 / dinamic
    # LAN1-VLAN1_SUBNET_ADDRESS_RANGE = Address range / dinamic

    for index, row in data.iterrows():  # AT MOST O(2n^2)

        row_dynamic = []

        for i in range(row.size):  # O(N)
            try:
                if row['ORGANIZATION'] != 'NOC':
                    row_dynamic.append([row['ORGANIZATION'], row['LAN1-VLAN' + str(i+1) + '_DOMAIN'], row['LAN1-VLAN' + str(i+1) + '_ZONE'], row['LAN1-VLAN' + str(i+1) + '_SUBNET_NAME'], row['LAN1-VLAN' + str(
                        i+1) + '_SUBNET'], row['LAN1-VLAN' + str(i+1) + '_SUBNET_DNS1'], row['LAN1-VLAN' + str(i+1) + '_SUBNET_DNS2'], row['LAN1-VLAN' + str(i+1) + '_SUBNET_ADDRESS_RANGE']])
            except Exception as error:
                # print('PASS THE NEXT ROW.')
                break

        for item in row_dynamic:  # O(N)
            subnet_name = item[3]  # row['LAN1-VLAN1_SUBNET_NAME']
            mask = item[4] # row['LAN1-VLAN1_SUBNET']
            add_range = item[7] # str(row.loc['LAN1-VLAN1_SUBNET_ADDRESS_RANGE'])
            min_ip, max_ip = add_range.split(' -- ', 1)
            subnet_address = str(ipaddress.IPv4Address(min_ip) - 1)
            min_plus = str(ipaddress.IPv4Address(min_ip) + 1)
            subnet = ipaddress.ip_network(subnet_address + mask)
            subnet_netmask = str(subnet.netmask)
            enterprise_name = item[0] # row.loc['ORGANIZATION']
            domain_name = item[1]  # row.loc['LAN1-VLAN1_DOMAIN']
            domain_name = replace_many(domain_name, [' ', '&'], '_')
            zone_name = item[2]  # row.loc['LAN1-VLAN1_ZONE']
            # subnet_gateway = row.loc['LAN1-VLAN1_GATEWAY']
            domain_name = replace_many(domain_name, ['<', '>'], '')
            zone_name = replace_many(zone_name, ['<', '>'], '')
            # subnet_gateway = replace_many(subnet_gateway, ['<', '>'], '')
            subnet_dns1 = item[5] # row.loc['LAN1-VLAN1_SUBNET_DNS1']
            subnet_dns2 = item[6] # row.loc['LAN1-VLAN1_SUBNET_DNS2']

            enterprise = domain = zone = "NoneType"
            
            try:
                # GET ALL PARAMETERS
                enterprise = nuage_user.enterprises.get_first(
                    filter=f'name is "{enterprise_name}"')
                domain = enterprise.domains.get_first(
                    filter=f'name is "{domain_name}"')
                zone = domain.zones.get_first(filter=f'name is "{zone_name}"')

                # WE CAN CONTINUE
                subnet_created = create_subnet(zone, zone_name, domain_name, subnet_name, subnet_address, subnet_netmask, min_ip)
                address_range = address_range_subnet(subnet_created, min_plus, max_ip)
                # dns_to_subnet(subnet_created, subnet_dns1, subnet_dns2) #working
                # delete_subnet(nuage_user, subnet_name, zone)
            except Exception as error:
                if enterprise == "NoneType" or enterprise == None:
                    logging.error(
                        f'Error Enterprise {enterprise_name} does not exist : {error}')
                if domain == "NoneType" or domain == None:
                    logging.error(
                        f'Error Dommain {domain_name}  does not exist in Enterprise {enterprise_name}: {error}')
                if zone == "NoneType" or zone == None:
                    logging.error(
                        f'Error Zone {zone_name} does not exist in Domain {domain_name} domain tiene: {domain}: {error}')
                else:
                    logging.error(
                        f'Error general: {error}')
