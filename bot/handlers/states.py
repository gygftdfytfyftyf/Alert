from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class CreateTagState(StatesGroup):
    waiting_name = State()


class RenameTagState(StatesGroup):
    waiting_name = State()


class AssignMembersState(StatesGroup):
    selecting = State()
    waiting_manual = State()
