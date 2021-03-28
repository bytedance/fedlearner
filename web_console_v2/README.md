## Web console V2 is working in progress

### Docker 
```shell
docker build -t fedlearner_webconsole_v2 .
docker run --rm -it -p 1989:1989 -p 1990:1990 fedlearner_webconsole_v2
```
Then visiting http://localhost:1989/ for the UI.
