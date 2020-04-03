import os
import shutil

from charmhelpers.core import hookenv, unitdata

from charms.reactive import (when, when_file_changed, remove_state,
                             when_not, set_state)

from charms.layer import tls_client
from charms.layer.metamorphosis import (METAMORPHOSIS_CA_CERT,
                                        METAMORPHOSIS_CERT,
                                        METAMORPHOSIS_KEY)
from charms.reactive.helpers import data_changed


@when('certificates.available')
def send_data():
    assertDirExists(METAMORPHOSIS_CERT)
    # Request a server cert with this information.
    tls_client.request_client_cert(
        hookenv.service_name(),
        crt_path=METAMORPHOSIS_CERT,
        key_path=METAMORPHOSIS_KEY)


@when_file_changed(
    METAMORPHOSIS_CA_CERT, METAMORPHOSIS_CERT, METAMORPHOSIS_KEY)
def restart_when_cert_key_changed():
    remove_state('metamorphosis.started')
    set_state('metamorphosis.reconfigure')


@when('tls_client.ca_installed')
@when_not('metamorphosis.ca.certificate.saved')
def import_ca_crt_to_keystore():
    ca_path = '/usr/local/share/ca-certificates/{}.crt'.format(
        hookenv.service_name()
    )

    if os.path.isfile(ca_path):
        shutil.copyfile(ca_path, METAMORPHOSIS_CA_CERT)
        remove_state('tls_client.ca_installed')
        set_state('metamorphosis.ca.certificate.saved')


def assertDirExists(path):
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path), exist_ok=True)


@when('endpoint.certificates.departed')
def clear_certificates():
    if os.path.exists(METAMORPHOSIS_CA_CERT):
        os.remove(METAMORPHOSIS_CA_CERT)

    certs_paths = unitdata.kv().get('layer.tls-client.cert-paths', {})
    if os.path.exists(METAMORPHOSIS_CERT):
        os.remove(METAMORPHOSIS_CERT)
    if os.path.exists(METAMORPHOSIS_KEY):
        os.remove(METAMORPHOSIS_KEY)

    for common_name, paths in certs_paths.get('client', {}).items():
        data_changed(
            'layer.tls-client.client.{}'.format(
                common_name
            ),
            {}
        )

    # We need to clean up data because the underlying layer
    # failes to clear flags and data_changed states when
    # we remove {charm}-easyrsa relation.
    unitdata_keys = (
        'reactive.tls_client',
        'reactive.data_changed.endpoint.certificates',
        'reactive.data_changed.ca_certificate',
        'reactive.data_changed.certificate',
        'reactive.data_changed.client',
        'reactive.data_changed.server',
        'reactive.states.endpoint.certificates',
        'reactive.states.tls_client'
        'reactive.data_changed.layer.tls-client'
    )
    for k in unitdata_keys:
        unitdata.kv().unsetrange(None, k)

    cleanup_states = (
        'tls_client.ca.saved',
        'tls_client.server.certificate.saved',
        'tls_client.server.key.saved',
        'metamorphosis.ca.certificate.saved'
    )
    for s in cleanup_states:
        remove_state(s)
