from marshmallow import Schema, fields


class UserSchema(Schema):
    id = fields.Integer(load_only=True)
    username = fields.String(required=True)
    total_point = fields.Integer()


class GameSessionSchema(Schema):
    id = fields.Integer(load_only=True)
    game_type = fields.String(required=True)
    chat_id = fields.Integer(required=True)
    words = fields.List(fields.String())
    next_user_id = fields.Integer(load_only=True)
    next_user = fields.Nested(UserSchema, load_only=True)
    creator_id = fields.Integer(load_only=True)
    creator = fields.Nested(UserSchema, load_only=True)
    winner_id = fields.Integer()
    winner = fields.Nested(UserSchema)
    is_active = fields.Boolean(required=True, load_only=True)
    next_start_letter = fields.String(load_only=True)
    current_poll_id = fields.Integer(load_only=True)


class CitySchema(Schema):
    id = fields.Integer(load_only=True)
    name = fields.String(required=True)


class CityListResponseSchema(Schema):
    cities = fields.List(fields.Nested(CitySchema))


class GameSessionListResponseSchema(Schema):
    games = fields.List(fields.Nested(GameSessionSchema))


class PlayerListResponseSchema(Schema):
    users = fields.List(fields.Nested(UserSchema))


class PaginationSchema(Schema):
    page = fields.Integer(default=1)
    per_page = fields.Integer(default=20)


class GameSettingsSchema(Schema):
    response_time = fields.Integer(default=15, required=False)
    anonymous_poll = fields.Boolean(default=True, required=False)
    poll_time = fields.Integer(default=15, required=False)
    life = fields.Integer(default=3, required=False)


class PaginationSchemaGames(Schema):
    page = fields.Integer(default=1)
    per_page = fields.Integer(default=20)
