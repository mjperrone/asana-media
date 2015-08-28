# asana-media
Service to easily add links to your asana project to read later!


##Build
```
packer build build/packer.json
```

Grab the ami id from that output for the deploy.

##Deploy
Replace the ami id in [deploy/deploy.tf](deploy/deploy.tf) with the one from the
packer build.
```
cd deploy/ && terraform apply
```
