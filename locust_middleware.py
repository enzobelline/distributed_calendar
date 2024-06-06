from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def load_test(self):
        self.client.post("/api/generate_load", json={"num_requests": 100})
