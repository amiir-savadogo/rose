import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('risks', '0004_alter_keyriskindicator_seuil_limite'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategorieEvenement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=30, unique=True)),
                ('libelle', models.CharField(max_length=200)),
                ('ordre', models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                'verbose_name': "Catégorie d'événement",
                'verbose_name_plural': "Catégories d'événement",
                'ordering': ['ordre', 'libelle'],
            },
        ),
        migrations.CreateModel(
            name='SousCategorieEvenement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('libelle', models.CharField(max_length=200)),
                ('exemples', models.TextField(blank=True, help_text='Un exemple par ligne')),
                ('ordre', models.PositiveSmallIntegerField(default=0)),
                ('categorie', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sous_categories', to='risks.categorieevenement')),
            ],
            options={
                'verbose_name': "Sous-catégorie d'événement",
                'verbose_name_plural': "Sous-catégories d'événement",
                'ordering': ['categorie__ordre', 'ordre', 'libelle'],
            },
        ),
        migrations.AddConstraint(
            model_name='souscategorieevenement',
            constraint=models.UniqueConstraint(fields=('categorie', 'libelle'), name='unique_sous_categorie_par_categorie'),
        ),
        migrations.AddField(
            model_name='risk',
            name='sous_categorie_evenement',
            field=models.ForeignKey(blank=True, help_text="Classification de l'annexe de la Circulaire 003-2017/CB/C", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='risques', to='risks.souscategorieevenement', verbose_name="Type d'événement (Bâle)"),
        ),
    ]
