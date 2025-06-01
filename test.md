source .venv/bin/activate
python manage.py makemigrations core
python manage.py makemigrations cart
python manage.py makemigrations catalog
python manage.py makemigrations orders
python manage.py makemigrations users

python manage.py migrate core
python manage.py migrate cart
python manage.py migrate catalog
python manage.py migrate orders
python manage.py migrate users

python manage.py makemigrations
python manage.py migrate

python manage.py createsuperuser

отдельном терминале
python manage.py seed_data

отдельном терминале
python manage.py runserver --verbosity 3

отдельном терминале
python manage.py run_sheduler


SELECT 
    relname AS table_name,
    n_live_tup AS estimated_rows
FROM 
    pg_stat_user_tables
ORDER BY 
    n_live_tup DESC;

UPDATE catalog_ribbon SET photo = 'ribbons/ribon.jpg';
UPDATE catalog_flower SET photo = 'flowers/flower_CuBhdQ0.jpg';
UPDATE catalog_bouquet SET photo = 'bouquets/bouqet.webp';
 UPDATE catalog_wrapper SET photo = 'wrappers/wrapper.jpg';
