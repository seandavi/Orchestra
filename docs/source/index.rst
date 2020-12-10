.. Orchestra documentation master file, created by
   sphinx-quickstart on Sat Aug 15 20:35:43 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Orchestra's documentation!
=====================================

Orchestra is a platform for running `custom` computing environments, each in the form of a Docker_ image, that can be shared and used by many remote users. For example, an Rstudio_ interface to a set of hands-on workshops can be shared with the entire class, eliminating software version and installation issues. A pre-installed set of python packages and associated `Jupyter notebooks`_ can accompany an institution`s published papers, allowing reviewers and interested readers to gain access to the exact data, software, and environment used in the manuscript. A complex web application that ingests user data could run inside the user's unique, private instance and when the instance is deleted, all user data is removed.

.. _Docker: https://docker.io
.. _`Jupyter notebooks`: https://jupyter.org
.. _Rstudio: https://rstudio.com


Starting the cluster
--------------------

.. code-block:: bash
   gcloud beta container --project "nih-strides-orchestra" clusters create "orchestra" --zone "us-central1-c" --no-enable-basic-auth --cluster-version "1.17.13-gke.2001" --release-channel "regular" --machine-type "e2-medium" --image-type "COS" --disk-type "pd-standard" --disk-size "100" --metadata disable-legacy-endpoints=true --scopes "https://www.googleapis.com/auth/devstorage.read_only","https://www.googleapis.com/auth/logging.write","https://www.googleapis.com/auth/monitoring","https://www.googleapis.com/auth/servicecontrol","https://www.googleapis.com/auth/service.management.readonly","https://www.googleapis.com/auth/trace.append" --num-nodes "3" --enable-stackdriver-kubernetes --enable-ip-alias --network "projects/nih-strides-orchestra/global/networks/default" --subnetwork "projects/nih-strides-orchestra/regions/us-central1/subnetworks/default" --default-max-pods-per-node "110" --no-enable-master-authorized-networks --addons HorizontalPodAutoscaling,HttpLoadBalancing --enable-autoupgrade --enable-autorepair --max-surge-upgrade 1 --max-unavailable-upgrade 0 --labels project=orchestra && gcloud beta container --project "nih-strides-orchestra" node-pools create "pool-1" --cluster "orchestra" --zone "us-central1-c" --machine-type "e2-highmem-4" --image-type "COS" --disk-type "pd-standard" --disk-size "200" --metadata disable-legacy-endpoints=true --scopes "https://www.googleapis.com/auth/devstorage.read_only","https://www.googleapis.com/auth/logging.write","https://www.googleapis.com/auth/monitoring","https://www.googleapis.com/auth/servicecontrol","https://www.googleapis.com/auth/service.management.readonly","https://www.googleapis.com/auth/trace.append" --num-nodes "3" --enable-autoscaling --min-nodes "0" --max-nodes "20" --enable-autoupgrade --enable-autorepair --max-surge-upgrade 1 --max-unavailable-upgrade 0


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   technical

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
