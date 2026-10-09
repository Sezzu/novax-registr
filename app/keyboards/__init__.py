from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app import texts as t


def buttons(rows):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label, callback_data=data) for label, data in row] for row in rows])


def event_keyboard(eid, registered=False):
    actions = ('edit', 'cancel', 'rules') if registered else ('join', 'rules')
    rows = [[(t.REGISTERED_RULES if registered and action == 'rules' else t.BUTTONS[action], f'{action}:{eid}')] for action in actions]
    if not registered:
        rows.append([(t.OTHER_EVENTS, 'events:list')])
    return buttons(rows)


def teams():
    return buttons([[(label, f'team:{key}')] for key, label in t.TEAMS.items()])


def consent():
    return buttons([[(t.YES, 'consent:yes'), (t.NO, 'consent:no')]])


def approve(token, publication=False):
    if publication:
        return buttons([[(t.PUBLISH, f'confirm:{token}')], [(t.EDIT_POST, f'postedit:{token}'), (t.ABORT, 'abort')]])
    return buttons([[(t.CONFIRM, f'confirm:{token}'), (t.ABORT, 'abort')]])


def home():
    return buttons([[(label, f'home:{key}')] for key, label in t.HOME_BUTTONS.items()])


def edit_fields(eid):
    return buttons([[(label, f'field:{eid}:{field}')] for field, label in t.EDIT_LABELS.items()] + [[(t.BACK_PREVIEW, f'preview:{eid}')], [('◀️ К событию', f'adm:event:{eid}')]])


def channel(url):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t.PARTICIPATE, url=url)]])
