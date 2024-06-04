Start MongoDB:

sh
    ./mongod.exe

Run the Flask Application:
    python middleware_lib_protocol.py

Access the Application:

Open a web browser and navigate to http://localhost:5000.
Fill out the form and click "Add Event".

Verify Data in MongoDB:
    ./mongosh.exe "mongodb://localhost:27017"
    use calendar
    db.events.find().pretty()












Step 2: Build and Run Your Docker Image
Navigate to Your Project Directory:
Open a terminal and navigate to your project directory where your Dockerfile is located.
    cd C:\Users\laure\Desktop\Masters\Spring 2024\CSEN317\project\root\docker_image

Build Your Docker Image:
Run the following command to build your Docker image:
    docker build -t my-calendar-app .

Run Your Docker Container:
After the image is built, run a container from your image:
    docker run -p 8080:8080 my-calendar-app



Step 3: Deploy to AWS Fargate
Once Docker is set up and you've successfully built and run your Docker image locally, you can proceed to deploy it to AWS Fargate using the steps outlined previously:

Create an ECS Cluster:
    aws ecs create-cluster --cluster-name myCluster

Register Task Definition:
    aws ecs register-task-definition --cli-input-json file://task-def.json

Create ECS Service:
    aws ecs create-service --cluster myCluster --service-name myService --ta