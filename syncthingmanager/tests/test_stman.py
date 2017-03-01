from unittest import TestCase

def device1_info(s):
    cfg = s.system.config()
    a = filter(lambda x: x['name'] == 'SyncthingManagerTestDevice1', cfg['devices'])
    return a

def folder1_info(s):
    cfg = s.system.config()
    a = filter(lambda x: x['id'] == 'stmantest1', cfg['folders']) 
    return a

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
    a = device1_info(s)
    s.remove_device('SyncthingManagerTestDevice1')
    b = device1_info(s)
    assert not next(b, False)

def test_edit_device(s):
    a = next(device1_info(s))
    s.edit_device('SyncthingManagerTestDevice1', 'introducer', True)
    s.edit_device('SyncthingManagerTestDevice1', 'compression', 'always')
    address = ['tcp://127.0.0.2:8384']
    s.edit_device('SyncthingManagerTestDevice1', 'addresses', address)
    b = next(device1_info(s))
    assert b['introducer']
    assert a['compression'] != 'always'
    assert b['compression'] == 'always'
    assert b['addresses'] == address

def test_device_add_address(s):
    a = next(device1_info(s))
    s.device_add_address('SyncthingManagerTestDevice1', 'tcp://127.0.0.2:8384')
    b = next(device1_info(s))
    assert 'tcp://127.0.0.2:8384' not in a['addresses']
    assert 'tcp://127.0.0.2:8384' in b['addresses']

def test_device_remove_address(s):
    a = next(device1_info(s))
    s.device_remove_address('SyncthingManagerTestDevice1', 'localhost')
    b = next(device1_info(s))
    assert 'localhost' in a['addresses']
    assert 'localhost' not in b['addresses']

def test_device_change_name(s):
    a = next(device1_info(s))
    s.device_change_name('SyncthingManagerTestDevice1', 'SyncthingManagerTestDevice2')
    b = next(filter(lambda x: x['name'] == 'SyncthingManagerTestDevice2', s.system.config()['devices']))
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
    a = folder1_info(s)
    assert next(a, False)
    s.remove_folder('stmantest1')
    b = folder1_info(s)
    assert not next(b, False)

def test_share_folder(s):
    a = folder1_info(s)
    s.share_folder('stmantest1', 'SyncthingManagerTestDevice1')
    b = folder1_info(s)
    assert len(next(a)['devices']) == 1
    assert len(next(b)['devices']) == 2

def test_folder_edit(s):
    a = next(folder1_info(s))
    s.folder_edit('stmantest1', 'label', 'SyncthingManagerTestFolder2')
    b = next(folder1_info(s))
    assert a['label'] == 'SyncthingManagerTestFolder1'
    assert b['label'] == 'SyncthingManagerTestFolder2'

def test_folder_set_label(s):
    a = next(folder1_info(s))
    s.folder_set_label('stmantest1', 'SyncthingManagerTestFolder2')
    b = next(folder1_info(s))
    assert a['label'] == 'SyncthingManagerTestFolder1'
    assert b['label'] == 'SyncthingManagerTestFolder2'

def test_folder_set_rescan(s):
    a = next(folder1_info(s))
    s.folder_set_rescan('stmantest1', 40)
    b = next(folder1_info(s))
    assert a['rescanIntervalS'] == 60
    assert b['rescanIntervalS'] == 40

def test_folder_set_minfree(s):
    a = next(folder1_info(s))
    s.folder_set_minfree('stmantest1', 5)
    b = next(folder1_info(s))
    assert a['minDiskFreePct'] == 0
    assert b['minDiskFreePct'] == 5

def test_folder_set_type(s):
    a = next(folder1_info(s))
    s.folder_set_type('stmantest1', 'readonly')
    b = next(folder1_info(s))
    assert a['type'] == 'readwrite'
    assert b['type'] == 'readonly'
