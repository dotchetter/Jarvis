#Create a ubuntu base image with python 3 installed.
FROM python:3.12

#Set the working directory
WORKDIR /

#copy all the files
COPY . .

#Install the dependencies
RUN apt-get -y update
RUN apt-get update && apt-get install -y python3 python3-pip
RUN pip3 install -r requirements.txt

#Expose the required port for MongoDB Atlas
EXPOSE 42487

# Run migrations and start Jarvis
CMD pyttman runfile jarvis jarvis/migrations/migrate.py upgrade
CMD pyttman runclient jarvis