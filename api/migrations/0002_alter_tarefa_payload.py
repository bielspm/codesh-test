from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tarefa',
            name='payload',
            field=models.TextField(),
        ),
    ]
