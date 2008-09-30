# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2005-2008 Async Open Source <http://www.async.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
""" Create all objects for an example database used by Stoq applications"""

from kiwi.component import provide_utility
from kiwi.environ import environ

from stoqlib.database.interfaces import ICurrentBranch, ICurrentBranchStation
from stoqlib.domain.station import BranchStation
from stoqlib.database.runtime import new_transaction
from stoqlib.domain.examples import log
from stoqlib.domain.examples.purchase import create_purchases
from stoqlib.domain.examples.sale import create_sales
from stoqlib.domain.examples.transfer import create_transfer
from stoqlib.importers.branchimporter import BranchImporter
from stoqlib.importers.clientimporter import ClientImporter
from stoqlib.importers.creditproviderimporter import CreditProviderImporter
from stoqlib.importers.employeeimporter import EmployeeImporter
from stoqlib.importers.productimporter import ProductImporter
from stoqlib.importers.serviceimporter import ServiceImporter
from stoqlib.importers.supplierimporter import SupplierImporter
from stoqlib.importers.transporterimporter import TransporterImporter
from stoqlib.lib.parameters import sysparam

def _import_one(klass, filename):
    imp = klass()
    imp.feed_file(environ.find_resource('csv', filename))

def _set_person_utilities():
    trans = new_transaction()
    branch = sysparam(trans).MAIN_COMPANY
    provide_utility(ICurrentBranch, branch)

    station = BranchStation(name=u"Stoqlib station", branch=branch,
                            connection=trans, is_active=True)
    provide_utility(ICurrentBranchStation, station)
    trans.commit()

def create(utilities=False):
    log.info('Creating example database')
    _import_one(BranchImporter, 'branches.csv')
    _import_one(CreditProviderImporter, 'creditproviders.csv')
    _import_one(SupplierImporter, 'suppliers.csv')
    _import_one(TransporterImporter, 'transporters.csv')
    _import_one(EmployeeImporter, 'employees.csv')
    _import_one(ClientImporter, 'clients.csv')
    if utilities:
        _set_person_utilities()
    _import_one(ProductImporter, 'products.csv')
    _import_one(ServiceImporter, 'services.csv')

    # FIXME: Move all examples to CSV files, they are easier to customize
    #        and to add additional example data.
    # NOTE: Do not add new examples which are not in csv format
    create_sales()
    create_purchases()
    create_transfer()
