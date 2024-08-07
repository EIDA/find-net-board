# Generated by Django 5.0.4 on 2024-04-16 14:11

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("board", "0001_initial"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Tests",
            new_name="Test",
        ),
        migrations.RemoveConstraint(
            model_name="test",
            name="unique_combination_tests",
        ),
        migrations.AddConstraint(
            model_name="test",
            constraint=models.UniqueConstraint(
                fields=("test_time", "network"), name="unique_combination_test"
            ),
        ),
    ]
