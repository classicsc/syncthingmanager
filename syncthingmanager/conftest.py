import syncthingmanager as stman
import pytest
import os


# classicsc
test_deviceID = 'MFZWI3D-BONSGYC-YLTMRWG-C43ENR5-QXGZDMM-FZWI3DP-BONSGYY-LTMRWAD'

# oneyb
if os.getenv('USER') == 'oney':
    test_deviceID = \
        'MH3SMD5-Q66HTXW-YXD77D4-JT3UJPF-APV5KPQ-REZBQWI-QQYNSSV-RGGRSQW'


@pytest.fixture(scope='session')
def temp_folder(tmpdir_factory):
    return tmpdir_factory.mktemp('stmantest1')

@pytest.fixture()
def s(request, temp_folder):
    APIInfo = stman.getAPIInfo(stman.__DEFAULT_CONFIG_LOCATION__)
    s = stman.SyncthingManager(APIInfo['APIkey'], APIInfo['Hostname'], APIInfo['Port'])
    cfg = s.system.config()
    cfga = s.system.config()
    test_device = {'deviceID': test_deviceID,
            'name': 'SyncthingManagerTestDevice1', 'addresses': ['localhost']}
    test_folder = {'id': 'stmantest1', 'label': 'SyncthingManagerTestFolder1',
            'path': str(temp_folder), 'type': 'readwrite', 'rescanIntervalS': 60,
            'devices': []}
    cfg['devices'].append(test_device)
    cfg['folders'].append(test_folder)
    s.system.set_config(cfg)
    yield s
    cfg = cfga
    s.system.set_config(cfg)
