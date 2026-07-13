# How to use

1. Put your gemini api key in `k8s/labarq-rag.yaml` (this will change whenever I start using a keyvault)
2. Build the docker image by executing `eval $(minikube docker-env); docker build -t labarq-rag:0.6 .`
3. Add `rag.com` to your `/etc/host`
   1. Execute `minikube ip` to get the IP address of your localcluster
   2. Add `<previous IP address>    rag.com`
4. Apply both yaml files inside the `k8s` folder (`kubectl apply -f <filename>`)
5. Apply migrations
   1. Get the name of the labarq-rag pod with `kubectl get pods`
   2. `kubectl exec -it <labarq-rag pod name> -- alembic upgrade head`
6. Add documents to your database by sending a POST request to `rag.com/documents` with a json containing a `name` and a `content` field
   * I like to create json files with `name` and `content` and execute the command `curl -X POST --json @filename.json rag.com/documents`  
7. Open [rag.com](http://rag.com) and ask some question about the documents you provided

# Requirements

* Docker
* Minikube
* Kubectl

# TODO

* Move secrets into keyvault
* Include k8s health checks
* Automatically manage app version
* Improving chunking (the current approach is pretty lame)
