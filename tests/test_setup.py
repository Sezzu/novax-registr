import setup_env
from dotenv import dotenv_values


def test_setup_preserves_token_and_sets_admin(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(setup_env, '__file__', str(tmp_path / 'setup_env.py'))
    token = '123456:' + 'x' * 35
    env = tmp_path / '.env'
    env.write_text(f'BOT_TOKEN={token}\nADMIN_IDS=\nCHANNEL_ID=\n', encoding='utf-8')
    monkeypatch.setattr('builtins.input', lambda _: '99887766')
    setup_env.main()
    values = dotenv_values(env)
    assert values['BOT_TOKEN'] == token
    assert values['ADMIN_IDS'] == '99887766'
    assert token not in capsys.readouterr().out
