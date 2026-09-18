import base64
import io
from PIL import Image


def register(client, email):
    r = client.post('/api/v1/auth/register', json={
        'email': email, 'password': 'StrongPass123!', 'full_name': 'Test User',
        'age_group': '25-34', 'interests': ['Tarot'], 'goals': ['Self Reflection']
    })
    assert r.status_code == 200, r.text
    return r.json()


def login(client, email):
    r = client.post('/api/v1/auth/login', data={'username': email, 'password': 'StrongPass123!'})
    assert r.status_code == 200, r.text
    return {'Authorization': f"Bearer {r.json()['access_token']}"}


def palm_payload():
    image = Image.new('RGB', (240, 240), 'white')
    buf = io.BytesIO(); image.save(buf, format='PNG')
    return {'image_base64': 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()}


def test_registration_forces_user_role(client):
    user = register(client, 'one@example.com')
    assert user['role'] == 'USER'


def test_tarot_reading_is_persisted_and_scoped(client):
    register(client, 'two@example.com')
    headers = login(client, 'two@example.com')
    cards = client.get('/api/v1/tarot/cards').json()
    card_ids = [cards[0]['id'], cards[1]['id'], cards[2]['id']]
    r = client.post('/api/v1/tarot/readings', headers=headers, json={
        'spread_name': 'three', 'focus_intent': 'career', 'card_ids': card_ids, 'reversed_flags': [False, True, False]
    })
    assert r.status_code == 200, r.text
    assert len(r.json()['cards_drawn']) == 3
    history = client.get('/api/v1/tarot/readings', headers=headers)
    assert history.status_code == 200 and len(history.json()) == 1


def test_user_cannot_access_another_users_palm_record(client, tmp_path):
    register(client, 'three@example.com'); h1 = login(client, 'three@example.com')
    from backend.app.services.palm_cv import palm_cv_service
    old = palm_cv_service.output_dir; palm_cv_service.output_dir = str(tmp_path)
    try:
        r = client.post('/api/v1/palm/analyze', headers=h1, json=palm_payload())
    finally:
        palm_cv_service.output_dir = old
    assert r.status_code == 200, r.text
    assert len(client.get('/api/v1/palm/readings', headers=h1).json()) == 1
    register(client, 'four@example.com'); h2 = login(client, 'four@example.com')
    assert client.get('/api/v1/palm/readings', headers=h2).json() == []


def test_report_exports_are_real_files_and_owner_scoped(client):
    register(client, 'export-one@example.com')
    h1 = login(client, 'export-one@example.com')
    cards = client.get('/api/v1/tarot/cards').json()
    r = client.post('/api/v1/tarot/readings', headers=h1, json={
        'spread_name': 'single', 'focus_intent': 'self reflection',
        'card_ids': [cards[0]['id']], 'reversed_flags': [False]
    })
    assert r.status_code == 200, r.text
    reading_id = r.json()['id']
    pdf = client.get(f'/api/v1/reports/pdf/tarot/{reading_id}', headers=h1)
    excel = client.get(f'/api/v1/reports/excel/tarot/{reading_id}', headers=h1)
    assert pdf.status_code == 200 and pdf.headers['content-type'].startswith('application/pdf') and pdf.content.startswith(b'%PDF')
    assert excel.status_code == 200 and 'spreadsheetml' in excel.headers['content-type'] and excel.content[:2] == b'PK'

    register(client, 'export-two@example.com')
    h2 = login(client, 'export-two@example.com')
    assert client.get(f'/api/v1/reports/pdf/tarot/{reading_id}', headers=h2).status_code == 404
    assert client.get(f'/api/v1/reports/excel/tarot/{reading_id}', headers=h2).status_code == 404


def test_user_analytics_isolation(client):
    register(client, 'analytics-one@example.com')
    h1 = login(client, 'analytics-one@example.com')
    cards = client.get('/api/v1/tarot/cards').json()
    client.post('/api/v1/tarot/readings', headers=h1, json={
        'spread_name': 'single', 'focus_intent': 'career',
        'card_ids': [cards[1]['id']], 'reversed_flags': [False]
    })
    a1 = client.get('/api/v1/analytics/user', headers=h1).json()
    register(client, 'analytics-two@example.com')
    h2 = login(client, 'analytics-two@example.com')
    a2 = client.get('/api/v1/analytics/user', headers=h2).json()
    assert a1['reading_count'] == 1
    assert a2['reading_count'] == 0
    assert a2['recent_readings'] == []


def test_personality_guidance_and_trend_report_exports_are_real_files(client):
    register(client, 'insight-reports@example.com')
    headers = login(client, 'insight-reports@example.com')
    cards = client.get('/api/v1/tarot/cards').json()
    reading = client.post('/api/v1/tarot/readings', headers=headers, json={
        'spread_name': 'single', 'focus_intent': 'career',
        'card_ids': [cards[0]['id']], 'reversed_flags': [False]
    })
    assert reading.status_code == 200, reading.text

    for report_type in ('personality', 'spiritual-guidance', 'insight-trend'):
        for fmt, signature, content_type in (
            ('pdf', b'%PDF', 'application/pdf'),
            ('excel', b'PK', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
        ):
            response = client.get(f'/api/v1/reports/{fmt}/{report_type}', headers=headers)
            assert response.status_code == 200, response.text
            assert response.headers['content-type'].startswith(content_type)
            assert response.content.startswith(signature)


def test_insight_report_exports_are_user_scoped(client):
    register(client, 'insight-owner@example.com')
    owner = login(client, 'insight-owner@example.com')
    cards = client.get('/api/v1/tarot/cards').json()
    reading = client.post('/api/v1/tarot/readings', headers=owner, json={
        'spread_name': 'single', 'focus_intent': 'self reflection',
        'card_ids': [cards[0]['id']], 'reversed_flags': [False]
    })
    assert reading.status_code == 200, reading.text

    register(client, 'insight-other@example.com')
    other = login(client, 'insight-other@example.com')
    assert client.get('/api/v1/reports/pdf/personality', headers=other).status_code == 404
    assert client.get('/api/v1/reports/excel/spiritual-guidance', headers=other).status_code == 404
    assert client.get('/api/v1/reports/pdf/insight-trend', headers=other).status_code == 404
