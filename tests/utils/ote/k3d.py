# Copyright (c) 2020, 2021, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl/
#

from .base import BaseEnvironment
import os
from string import Template
import subprocess
from tempfile import mkstemp
from setup.config import g_ts_cfg


class K3dEnvironment(BaseEnvironment):
    name = "k3d"
    cluster_name = "ote-mycluster"

    def load_images(self, images):
        loaded = []
        for img, is_latest in images:
            md = open(img+".txt")
            image_id = md.readline().strip()
            image_repo_tag = md.readline().strip()
            self.load_image(image_repo_tag, image_id)

    def load_image(self, repo_tag, id):
        print(f"Loading image {repo_tag} ({id})")
        cmd = f"k3d image import {repo_tag} -c {self.cluster_name}"
        print(cmd)
        subprocess.check_call(cmd, shell=True)

    def start_cluster(self, nodes, version, registry_cfg_path):
        assert version is None

        args = ["k3d", "cluster", "create", self.cluster_name, "--timeout", "5m"]
        if g_ts_cfg.image_registry:
            if not registry_cfg_path:
                registry_cfg_path = self.prepare_registry_cfg()
            args.extend(["--registry-config", registry_cfg_path])

        if self.operator_mount_path:
            args += ["--volume", f"{self.operator_mount_path}:{self.operator_host_path}"]

        subprocess.check_call(args)

        # connect network of the cluster to the local image registry
        if g_ts_cfg.image_registry:
            subprocess.call(["docker", "network", "connect", f"k3d-{self.cluster_name}", g_ts_cfg.image_registry_host])

    def stop_cluster(self):
        args = ["k3d", "cluster", "stop", self.cluster_name]
        subprocess.check_call(args)

    def delete_cluster(self):
        args = ["k3d", "cluster", "delete", self.cluster_name]
        subprocess.check_call(args)

    def prepare_registry_cfg(self):
        cfg_template = f"""mirrors:
  "docker.io":
    endpoint:
      - http://$registry
  "$registry":
    endpoint:
      - http://$registry
"""
        data = {
            'registry': g_ts_cfg.image_registry
        }

        tmpl = Template(cfg_template)
        contents = tmpl.substitute(data)
        fd, path = mkstemp(prefix="k3d-registry", suffix=".yaml")
        with os.fdopen(fd, 'w') as f:
            f.write(contents)
        return path