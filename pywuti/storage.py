#!/usr/bin/python
#
# Copyright (C) 2016 Openwrt x86_64 Unity Project
#
# Wei Yongjun <weiyj.lk@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation; either version 2.1 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import logging
import subprocess

class Device(object):
    def __init__(self):
        pass

class Storage(object):
    def __init__(self, disk, instroot):
        self._instroot = instroot
        self._disk = disk

        self.partitions = []

        self.mountOrder = []
        self.unmountOrder = []

    def add_partition(self, size, mountpoint, fstype = None):
        self.partitions.append({
            'size': size,
            'mountpoint': mountpoint, # Mount relative to chroot
            'fstype': fstype,
            'device': None, # kpartx device node for partition
            'mount': None, # Mount object
            'UUID': None, # UUID for partition
            'num': None
        }) # Partition number

    def __format_disks(self):
        logging.debug("Formatting disks")
        logging.debug("Initializing partition table for %s with %s layout" % (self._disk, 'msdos'))
        try:
            rc = subprocess.call(["/usr/sbin/parted", "-s", self._disk, "mklabel", "%s" % 'msdos'])
            if rc != 0:
                logging.error("Error writing partition table on %s" % self._disk)
        except:
            logging.error("Error writing partition table on %s" % self._disk)
        
        logging.debug("Assigning partitions to disks")
        offset = 0
        for n in range(len(self.partitions)):
            p = self.partitions[n]
            p['start'] = offset
            offset += p['size']
            p['device'] = "%s%d" % (self._disk, n + 1)
            p['type'] = 'primary'

        logging.debug("Creating partitions")
        for p in self.partitions:
            logging.debug("Add %s part at %d of size %d" % (p['type'], p['start'], p['size']))
            fstype = p['fstype']
            if p['fstype'] == 'vfat':
                fstype = 'fat32'

            try:
                rc = subprocess.call(["/usr/sbin/parted", "-a", "opt", "-s", self._disk, "mkpart",
                                  p['type'], fstype, "%dM" % p['start'], "%dM" % (p['start'] + p['size'])])
            except:
                logging.error("Error creating partition %s" % p['device'])

            try:
                rc = subprocess.call(["/usr/sbin/mkfs.%s" % fstype, "-q", "-F", p['device']])
            except:
                logging.error("Error format partition %s" % p['device'])

    def __calculate_mountorder(self):
        for p in self.partitions:
            self.mountOrder.append(p['mountpoint'])
            self.unmountOrder.append(p['mountpoint'])

        self.mountOrder.sort()
        self.unmountOrder.sort()
        self.unmountOrder.reverse()

    def unmount(self):
        for mp in self.unmountOrder:
            p = None

            if mp == 'swap':
                continue
            for p1 in self.partitions:
                if p1['mountpoint'] == mp:
                    p = p1
                    break

            try:
                subprocess.call(["/bin/umount", p['device']])
            except:
                pass

    def mount(self):
        self.__format_disks()
        self.__calculate_mountorder()

        print self.mountOrder
        for mp in self.mountOrder:
            p = None

            if mp == 'swap':
                continue
            for p1 in self.partitions:
                if p1['mountpoint'] == mp:
                    p = p1
                    break

            rpath = os.path.join(self._instroot, mp[1:])
            if not os.path.exists(rpath):
                os.makedirs(rpath)
            try:
                subprocess.call(["/bin/mount", "-t", p['fstype'], p['device'], rpath])
            except:
                pass
