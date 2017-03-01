from unittest import TestCase

def test_device_info(s):
    tc = TestCase()
    info = s.device_info('SyncthingManagerTestDevice1')
    tc.assertCountEqual(['id', 'index', 'folders', 'name'], list(info.keys()))
    assert info['index'] != None
    assert info['folders'] == []

def test_folder_info(s):
    tc = TestCase()
    info = s.folder_info('SyncthingManagerTestFolder1')
    tc.assertCountEqual(['id', 'index', 'devices', 'label'], list(info.keys()))
    assert len(info['devices']) == 1
    info = s.folder_info('stmantest1')
    tc.assertCountEqual(['id', 'index', 'devices', 'label'], list(info.keys()))

def test_add_device(s):
    s.add_device('MRIW7OK-NETT3M4-N6SBWME-N25O76W-YJKVXPH-FUMQJ3S-P57B74J-GBITBAC',
            'SyncthingManagerTestDevice2', '127.0.0.1', True, True)
    cfg = s.system.config()
    found = False
    for device in cfg['devices']:
        if device['deviceID'] == 'MRIW7OK-NETT3M4-N6SBWME-N25O76W-YJKVXPH-FUMQJ3S-P57B74J-GBITBAC':
            found = True
            assert device['introducer']
            assert 'dynamic' in device['addresses']
    assert found

def test_remove_device(s):
    cfg = s.system.config()
    a = filter(lambda x: x['name'] == 'SyncthingManagerTestDevice1', cfg['devices'])
    assert next(a, False)
    s.remove_device('SyncthingManagerTestDevice1')
    cfg = s.system.config()
    b = filter(lambda x: x['name'] == 'SyncthingManagerTestDevice1', cfg['devices'])
    assert not next(b, False)

def test_edit_device(s):
    cfg = s.system.config()
    a = next(filter(lambda x: x['name'] == 'SyncthingManagerTestDevice1', cfg['devices']))
    s.edit_device('SyncthingManagerTestDevice1', 'introducer', True)
    s.edit_device('SyncthingManagerTestDevice1', 'compression', 'always')
    address = ['tcp://127.0.0.2:8384']
    s.edit_device('SyncthingManagerTestDevice1', 'addresses', address)
    cfg = s.system.config()
    b = next(filter(lambda x: x['name'] == 'SyncthingManagerTestDevice1', cfg['devices']))
    assert b['introducer']
    assert a['compression'] != 'always'
    assert b['compression'] == 'always'
    assert b['addresses'] == address

def test_device_add_address(s):
    cfg = s.system.config()
    a = next(filter(lambda x: x['name'] == 'SyncthingManagerTestDevice1', cfg['devices']))
    s.device_add_address('SyncthingManagerTestDevice1', 'tcp://127.0.0.2:8384')
    cfg = s.system.config()
    b = next(filter(lambda x: x['name'] == 'SyncthingManagerTestDevice1', cfg['devices']))
    assert 'tcp://127.0.0.2:8384' not in a['addresses']
    assert 'tcp://127.0.0.2:8384' in b['addresses']

def test_device_remove_address(s):
    cfg = s.system.config()
    a = next(filter(lambda x: x['name'] == 'SyncthingManagerTestDevice1', cfg['devices']))
    s.device_remove_address('SyncthingManagerTestDevice1', 'localhost')
    cfg = s.system.config()
    b = next(filter(lambda x: x['name'] == 'SyncthingManagerTestDevice1', cfg['devices']))
    assert 'localhost' in a['addresses']
    assert 'localhost' not in b['addresses']

def test_device_change_name(s):
    cfg = s.system.config()
    a = next(filter(lambda x: x['name'] == 'SyncthingManagerTestDevice1', cfg['devices']))
    s.device_change_name('SyncthingManagerTestDevice1', 'SyncthingManagerTestDevice2')
    cfg = s.system.config()
    b = next(filter(lambda x: x['name'] == 'SyncthingManagerTestDevice2', cfg['devices']))
    assert a['name'] == 'SyncthingManagerTestDevice1'
    assert b['name'] == 'SyncthingManagerTestDevice2'

def test_add_folder(s, temp_folder):
    p = temp_folder
    s.add_folder(str(p), 'stmantest2', 'SyncthingManagerTestFolder2', 'readonly', 40)
    cfg = s.system.config()
    found = False
    for folder in cfg['folders']:
        if folder['id'] == 'stmantest2':
            found = True
            assert folder['type'] == 'readonly'
            assert folder['rescanIntervalS'] == 40
    assert found

def test_remove_folder(s):
    cfg = s.system.config()
    a = filter(lambda x: x['id'] == 'stmantest1', cfg['folders'])
    assert next(a, False)
    s.remove_folder('stmantest1')
    cfg = s.system.config()
    b = filter(lambda x: x['id'] == 'stmantest1', cfg['folders'])
    assert not next(b, False)

def test_share_folder(s):
    cfg = s.system.config()
    a = filter(lambda x: x['id'] == 'stmantest1', cfg['folders']) 
    s.share_folder('stmantest1', 'SyncthingManagerTestDevice1')
    cfg = s.system.config()
    b = filter(lambda x: x['id'] == 'stmantest1', cfg['folders']) 
    assert len(next(a)['devices']) == 1
    assert len(next(b)['devices']) == 2
