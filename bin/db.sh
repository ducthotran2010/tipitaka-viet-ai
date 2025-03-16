set -x
docker run -d -p 27017:27017 --name tipitaka-viet-mongodb mongodb/mongodb-atlas-local
docker run --name tipitaka-viet-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=postgres -p 5432:5432 -d postgres
