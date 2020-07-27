\connect workshop
drop table workshops;
create table workshops(id integer, description varchar, url varchar, container varchar);
\copy workshops(id,description, url, container) from 'workshops.csv' CSV header;
\x
select * from workshops;
