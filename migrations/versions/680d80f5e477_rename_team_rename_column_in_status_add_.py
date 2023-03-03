"""rename team, rename column in status, add word and used word

Revision ID: 680d80f5e477
Revises: 2748a52adac5
Create Date: 2023-03-02 08:46:39.981255

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '680d80f5e477'
down_revision = '2748a52adac5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###

    op.rename_table('teams', 'user_game_sessions')
    op.alter_column(table_name='game_sessions',
                    column_name='status',
                    new_column_name='is_active')

    op.create_table('words',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('word', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('word')
    )

    op.create_table('words_in_game',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('game_session_id', sa.Integer(), nullable=False),
    sa.Column('word_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['game_session_id'], ['game_sessions.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['word_id'], ['words.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.drop_table('answers')
    op.drop_table('questions')
    op.drop_table('themes')


    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.rename_table('user_game_sessions', 'teams')
    op.alter_column(table_name='game_sessions',
                    column_name='is_active',
                    new_column_name='status')

    op.create_table('themes',
    sa.Column('id', sa.INTEGER(), server_default=sa.text("nextval('themes_id_seq'::regclass)"), autoincrement=True, nullable=False),
    sa.Column('title', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name='themes_pkey'),
    sa.UniqueConstraint('title', name='themes_title_key'),
    postgresql_ignore_search_path=False
    )
    op.create_table('questions',
    sa.Column('id', sa.INTEGER(), server_default=sa.text("nextval('questions_id_seq'::regclass)"), autoincrement=True, nullable=False),
    sa.Column('title', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('theme_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['theme_id'], ['themes.id'], name='questions_theme_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='questions_pkey'),
    sa.UniqueConstraint('title', name='questions_title_key'),
    postgresql_ignore_search_path=False
    )
    op.create_table('answers',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('title', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('is_correct', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('question_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['question_id'], ['questions.id'], name='answers_question_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='answers_pkey')
    )
    op.drop_table('words_in_game')
    op.drop_table('words')
    # ### end Alembic commands ###
