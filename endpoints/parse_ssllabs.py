import simplejson
import datetime

def extractScanInfo(data):

    vuln_found = []

    vuln_msgs = {
    'fallbackScsv': 'This server does not support downgrade attack prevention',
    'forwardSecrecy': 'This server does not support Perfect Forward Secrecy',
    'freak': 'This server is vulnerable to the FREAK attack due to its support of export ciphers',
    'hasSct': 'this server does not support sct',
    'heartbeat': 'This server does not support the heartbeat extension',
    'heartbleed': 'this server is vulnerable to the heartbleed attack',
    'logjam': 'This server is vulnerable to the LOGJAM attack',
    'nonPrefixDelegation': 'non prefix delegation',
    'ocspStapling': 'This server does not support OCSP stapling',
    'openSslCcs': 'This server may be affected by the OpenSSL CCS vulnerability',
    'poodle': 'This server is vulnerable to the SSLv3 POODLE attack',
    'poodleTls': 'This server is vulnerable to the TLS POODLE attack',
    'rc4WithModern': 'This server supports RC4 in modern browsers',
    'renegSupport': 'This server does not support secure renegotiation',
    'sessionResumption': 'this server supports resumption',
    'supportsNpn': 'this server is vulnerable to npn',
    'supportsRc4': 'This server supports the weak RC4 cipher',
    'vulnBeast': 'This server has not mitigated the BEAST attack',
    'sslProtocol': 'This server supports the weak SSL protocol instead of TLS only',
    'sha1InCipher': 'This server supports the weak SHA1 hash',
    'md5InCipher': 'This server supports the weak MD5 hash',
    'sha1InCert': 'This certificate uses the weak SHA1 hash in its signature',
    'md5InCert': 'This certificate uses the weak MD5 hash in its signature',
    'certMismatch': 'Certificate name does not match host',
    'sha1InInterCert': 'Intermediate certificate with weak signature (SHA1)',
    'weakDHkey': 'This server supports a weak Diffie Hellman key',
    }

    vuln_list = [
    'freak',
    #'hasSct',
    'heartbleed',
    'logjam',
    #'nonPrefixDelegation',
    #'ocspStapling',
    'poodle',
    'rc4WithModern',
    #'sessionResumption',
    #'supportsNpn',
    'supportsRc4',
    'vulnBeast',
    ]

    expiry_secs = int(data[0]['endpoints'][0]['details']['cert']['notAfter'] / 1000)
    expiry_date = datetime.datetime.fromtimestamp(expiry_secs)

    details = data[0]['endpoints'][0]['details']

    for vuln in vuln_list:
        if details[vuln]:
            vuln_found.append(vuln_msgs[vuln])

    for prot in details['protocols']:
        if prot['name'] == "SSL":
            vuln_found.append(vuln_msgs['sslProtocol'])
            break

    # process cipher suites
    dhNeedsCheck = md5NeedsCheck = sha1NeedsCheck = True
    for suite in details['suites']['list']:
        if dhNeedsCheck  and  'dhStrength' in suite.keys()  and  suite['dhStrength'] <= 1024:
            vuln_found.append(vuln_msgs['weakDHkey'])
            dhNeedsCheck = False
        if md5NeedsCheck  and  'MD5' in suite['name']:
            vuln_found.append(vuln_msgs['md5InCipher'])
            md5NeedsCheck = False
        #if sha1NeedsCheck  and  suite['name'].endswith('_SHA'):
        #    vuln_found.append(vuln_msgs['sha1InCipher'])
        #    sha1NeedsCheck = False


    # process cert chain
    for cert in details['chain']['certs']:
        if 'SHA1' in cert['sigAlg']:
            vuln_found.append(vuln_msgs['sha1InInterCert'])
            break

    # process main cert
    if 'SHA1' in details['cert']['sigAlg']:
        vuln_found.append(vuln_msgs['sha1InCert'])

    if details['openSslCcs'] == 2:
        vuln_found.append(vuln_msgs['openSslCcs'])

    if details['poodleTls'] == 2:
        vuln_found.append(vuln_msgs['poodleTls'])

    if details['forwardSecrecy'] <= 1:
        vuln_found.append(vuln_msgs['forwardSecrecy'])

    if details['renegSupport'] == 0:
        vuln_found.append(vuln_msgs['renegSupport'])

    if data[0]['endpoints'][0]['grade'] == 'M':
        vuln_found.append(vuln_msgs['certMismatch'])

    if 'fallbackScsv' in details.keys()  and  not details['fallbackScsv']:
        vuln_found.append(vuln_msgs['fallbackScsv'])

    if 'heartbeat' in details.keys()  and  not details['heartbeat']:
        vuln_found.append(vuln_msgs['heartbeat'])

    return [data[0]['endpoints'][0]['grade'], vuln_found, expiry_date]

