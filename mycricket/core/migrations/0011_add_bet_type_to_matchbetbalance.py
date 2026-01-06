# Generated migration to add bet_type field to MatchBetBalance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_matchbet_matchbetbalance'),
    ]

    operations = [
        # Step 1: Remove old unique constraint
        migrations.AlterUniqueTogether(
            name='matchbetbalance',
            unique_together=set(),
        ),
        # Step 2: Add bet_type field (nullable)
        migrations.AddField(
            model_name='matchbetbalance',
            name='bet_type',
            field=models.CharField(blank=True, choices=[('back', 'Back'), ('lay', 'Lay')], help_text='Bet type (back or lay) for this balance entry', max_length=10, null=True),
        ),
        # Step 3: Add new unique constraint with bet_type
        # Note: SQLite allows multiple NULLs in unique constraints, so existing records with NULL bet_type won't conflict
        migrations.AlterUniqueTogether(
            name='matchbetbalance',
            unique_together={('match', 'user', 'selection', 'bet_type')},
        ),
        # Step 4: Add index for performance
        migrations.AddIndex(
            model_name='matchbetbalance',
            index=models.Index(fields=['match', 'user', 'bet_type'], name='core_matchb_match_i_bet_typ_idx'),
        ),
    ]

