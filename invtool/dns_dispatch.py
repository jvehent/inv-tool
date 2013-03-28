import requests

try:
    import simplejson as json
except ImportError:
    import json

from invtool.dispatch import Dispatch
from invtool.lib.registrar import registrar
from invtool.lib.config import API_MAJOR_VERSION, REMOTE, auth
from invtool.lib.options import (
    fqdn_argument, ttl_argument, ip_argument, view_arguments,
    description_argument, comment_argument, update_pk_argument,
    delete_pk_argument, target_argument, detail_pk_argument, priority_argument,
    port_argument, weight_argument
)


class DNSDispatch(Dispatch):
    def route(self, nas):
        if self.dtype.lower() == nas.dtype.lower():
            return getattr(self, nas.action.lower())(nas)

    def delete(self, nas):
        url = self.object_url.format(API_MAJOR_VERSION, self.resource_name,
                                     nas.pk)
        url = "{0}{1}?format=json".format(REMOTE, url)
        headers = {'content-type': 'application/json'}
        resp = requests.delete(url, headers=headers, auth=auth)
        return self.handle_resp(nas, {}, resp)

    def detail(self, nas):
        url = self.object_url.format(API_MAJOR_VERSION, self.resource_name,
                                     nas.pk)
        url = "{0}{1}?format=json".format(REMOTE, url)
        headers = {'content-type': 'application/json'}
        resp = requests.get(url, headers=headers, auth=auth)
        return self.handle_resp(nas, {}, resp)

    def update(self, nas):
        data = self.get_update_data(nas)  # Dispatch defined Hook
        tmp_url = self.object_url.format(API_MAJOR_VERSION, self.resource_name,
                                         nas.pk)
        url = "{0}{1}".format(REMOTE, tmp_url)
        return self.action(nas, url, requests.patch, data)

    def create(self, nas):
        data = self.get_create_data(nas)  # Dispatch defined Hook
        tmp_url = self.object_list_url.format(API_MAJOR_VERSION,
                                              self.resource_name)
        url = "{0}{1}".format(REMOTE, tmp_url)
        return self.action(nas, url, requests.post, data)

    def action(self, nas, url, method, data):
        headers = {'content-type': 'application/json'}
        data = json.dumps(data, indent=2)
        resp = method(url, headers=headers, data=data, auth=auth)
        return self.handle_resp(nas, data, resp)

    def get_create_data(self, nas):
        data = {}
        for add_arg, extract_arg, test_method in self.create_args:
            data.update(extract_arg(nas))
        return data

    def get_update_data(self, nas):
        data = {}
        for add_arg, extract_arg, test_method in self.update_args:
            data.update(extract_arg(nas))
        return data


def build_create_parser(dispatch, action_parser):
    create_parser = action_parser.add_parser('create', help="Create "
                                             "a(n) {0} record".format(
                                             dispatch.dtype))
    for add_arg, extract_arg, test_method in dispatch.create_args:
        add_arg(create_parser)


def build_update_parser(dispatch, action_parser):
    update_parser = action_parser.add_parser('update', help="Update "
                                             "a(n) {0} record".format(
                                             dispatch.dtype))
    for add_arg, extract_arg, test_method in dispatch.update_args:
        add_arg(update_parser, required=False)


def build_delete_parser(dispatch, action_parser):
    delete_parser = action_parser.add_parser('delete', help="Delete "
                                             "a(n) {0} record".format(
                                             dispatch.dtype))
    for add_arg, extract_arg, test_method in dispatch.delete_args:
        add_arg(delete_parser)


def build_detail_parser(dispatch, action_parser):
    detail_parser = action_parser.add_parser('detail', help="Detail "
                                             "a(n) {0} record".format(
                                             dispatch.dtype))
    for add_arg, extract_arg, test_method in dispatch.detail_args:
        add_arg(detail_parser)


def build_dns_parsers(base_parser):
    # Build all the records

    for dispatch in [d for d in registrar.dispatches if d.dgroup == 'dns']:
        record_base_parser = base_parser.add_parser(
            dispatch.dtype,
            help="The interface for {0} records".format(dispatch.dtype),
            add_help=True
        )
        action_parser = record_base_parser.add_subparsers(
            help="{0} record actions".format(dispatch.dtype),
            dest='action'
        )
        build_create_parser(dispatch, action_parser)
        build_update_parser(dispatch, action_parser)
        build_delete_parser(dispatch, action_parser)
        build_detail_parser(dispatch, action_parser)


class DispatchA(DNSDispatch):
    resource_name = 'addressrecord'
    dtype = 'A'
    dgroup = 'dns'
    ip_type = '4'

    create_args = [
        fqdn_argument('fqdn', dtype),  # ~> (labmda, lambda)
        ttl_argument('ttl'),
        ip_argument('ip_str', ip_type),
        view_arguments('views'),
        description_argument('description'),
        comment_argument('comment')
    ]

    update_args = create_args + [
        update_pk_argument('pk', dtype)
    ]

    delete_args = [
        delete_pk_argument('pk', dtype)
    ]

    detail_args = [detail_pk_argument('pk', dtype)]

    def get_create_data(self, nas):
        data = super(DispatchA, self).get_create_data(nas)
        data['ip_type'] = self.ip_type
        return data

    def get_update_data(self, nas):
        data = super(DispatchA, self).get_update_data(nas)
        data['ip_type'] = self.ip_type
        return data


class DispatchPTR(DNSDispatch):
    resource_name = 'ptr'
    dtype = 'PTR'
    dgroup = 'dns'

    create_args = [
        ttl_argument('ttl'),
        ip_argument('ip_str', '4'),
        view_arguments('views'),
        target_argument('name'),
        description_argument('description'),
        comment_argument('comment')
    ]

    update_args = create_args + [
        update_pk_argument('pk', dtype)
    ]

    delete_args = [
        delete_pk_argument('pk', dtype)
    ]

    detail_args = [detail_pk_argument('pk', dtype)]

    def determine_ip_type(self, ip_str):
        if ip_str.find(':') > -1:
            ip_type = '6'
        else:
            ip_type = '4'  # Default to 4
        return ip_type

    def get_create_data(self, nas):
        data = super(DispatchPTR, self).get_create_data(nas)
        data['ip_type'] = self.determine_ip_type(data.get('ip_str', ''))
        return data

    def get_update_data(self, nas):
        data = super(DispatchPTR, self).get_update_data(nas)
        data['ip_type'] = self.determine_ip_type(data.get('ip_str', ''))
        return data


class DispatchAAAA(DispatchA):
    dtype = 'AAAA'
    dgroup = 'dns'
    ip_type = '6'

    create_args = [
        fqdn_argument('fqdn', dtype),  # ~> (labmda, lambda)
        ttl_argument('ttl'),
        ip_argument('ip_str', ip_type),
        view_arguments('views'),
        description_argument('description'),
        comment_argument('comment')
    ]

    update_args = create_args + [
        update_pk_argument('pk', dtype)
    ]

    delete_args = [
        delete_pk_argument('pk', dtype)
    ]

    detail_args = [detail_pk_argument('pk', dtype)]


class DispatchCNAME(DNSDispatch):
    resource_name = 'cname'
    dtype = 'CNAME'
    dgroup = 'dns'

    create_args = [
        fqdn_argument('fqdn', dtype),  # ~> (labmda, lambda)
        ttl_argument('ttl'),
        target_argument('target'),
        view_arguments('views'),
        description_argument('description'),
        comment_argument('comment')
    ]

    update_args = create_args + [
        update_pk_argument('pk', dtype)
    ]

    delete_args = [
        delete_pk_argument('pk', dtype)
    ]

    detail_args = [detail_pk_argument('pk', dtype)]


class DispatchSRV(DNSDispatch):
    resource_name = 'srv'
    dtype = 'SRV'
    dgroup = 'dns'

    create_args = [
        fqdn_argument('fqdn', dtype),  # ~> (labmda, lambda)
        ttl_argument('ttl'),
        port_argument('port'),
        weight_argument('weight'),
        priority_argument('priority'),
        target_argument('target'),
        view_arguments('views'),
        description_argument('description'),
        comment_argument('comment')
    ]

    update_args = create_args + [
        update_pk_argument('pk', dtype)
    ]

    delete_args = [
        delete_pk_argument('pk', dtype)
    ]

    detail_args = [detail_pk_argument('pk', dtype)]


class DispatchMX(DNSDispatch):
    resource_name = 'mx'
    dtype = 'MX'
    dgroup = 'dns'

    create_args = [
        fqdn_argument('fqdn', dtype),  # ~> (labmda, lambda)
        ttl_argument('ttl'),
        priority_argument('priority'),
        target_argument('server'),
        view_arguments('views'),
        description_argument('description'),
        comment_argument('comment')
    ]

    update_args = create_args + [
        update_pk_argument('pk', dtype)
    ]

    delete_args = [
        delete_pk_argument('pk', dtype)
    ]

    detail_args = [detail_pk_argument('pk', dtype)]


class DispatchTXT(DNSDispatch):
    resource_name = 'txt'
    dtype = 'TXT'
    dgroup = 'dns'

    create_args = [
        fqdn_argument('fqdn', dtype),  # ~> (labmda, lambda)
        ttl_argument('ttl'),
        target_argument('txt_data'),
        view_arguments('views'),
        description_argument('description'),
        comment_argument('comment')
    ]

    update_args = create_args + [
        update_pk_argument('pk', dtype)
    ]

    delete_args = [
        delete_pk_argument('pk', dtype)
    ]

    detail_args = [detail_pk_argument('pk', dtype)]


registrar.register(DispatchA())
registrar.register(DispatchAAAA())
registrar.register(DispatchCNAME())
registrar.register(DispatchMX())
registrar.register(DispatchPTR())
registrar.register(DispatchSRV())
registrar.register(DispatchTXT())
