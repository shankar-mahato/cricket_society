# Generated migration to add 'session' choice to bet_type field in MatchBetBalance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_rename_core_matchb_match_i_bet_typ_idx_core_matchb_match_i_79b50a_idx'),
    ]

    operations = [
        migrations.AlterField(
            model_name='matchbetbalance',
            name='bet_type',
            field=models.CharField(blank=True, choices=[('back', 'Back'), ('lay', 'Lay'), ('session', 'Session')], help_text='Bet type (back, lay, or session) for this balance entry', max_length=10, null=True),
        ),
    ]

