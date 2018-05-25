# -*- coding: utf-8 -*-

# Copyright 2018 IBM.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================

import unittest
from collections import OrderedDict
from parameterized import parameterized

from test.common import QISKitAcquaChemistryTestCase
from qiskit_acqua_chemistry import FermionicOperator
from qiskit_acqua import get_algorithm_instance, get_optimizer_instance, get_variational_form_instance
from qiskit_acqua_chemistry.drivers import ConfigurationManager

#     pyscf_cfg = OrderedDict([('atom', 'Cl .0 .0 .0; H .0 .0 1.29'), ('unit', 'Angstrom'), ('charge', 0), ('spin', 0), ('basis', 'sto3g')])
#     pyscf_cfg = OrderedDict([('atom', 'Li .0 .0 .0; H .0 .0 1.595'), ('unit', 'Angstrom'), ('charge', 0), ('spin', 0), ('basis', 'sto3g')])

@unittest.skipUnless(QISKitAcquaChemistryTestCase.SLOW_TEST, 'slow')
class TestEnd2EndH2(QISKitAcquaChemistryTestCase):
    """End2End tests."""
    def setUp(self):
        self.variational_form = 'RYRZ'
        self.algorithm = 'VQE'
        self.log.debug('Testing VQE with H2')
        cfg_mgr = ConfigurationManager()
        pyscf_cfg = OrderedDict([('atom', 'H .0 .0 .0; H .0 .0 0.735'), ('unit', 'Angstrom'), ('charge', 0), ('spin', 0), ('basis', 'sto3g')])
        section = {}
        section['properties'] = pyscf_cfg
        driver = cfg_mgr.get_driver_instance('PYSCF')
        molecule = driver.run(section)

        ferOp = FermionicOperator(h1=molecule._one_body_integrals, h2=molecule._two_body_integrals)
        self.qubitOp = ferOp.mapping(map_type='JORDAN_WIGNER', threshold=0.00000001)

        exact_eigensolver = get_algorithm_instance('ExactEigensolver')
        exact_eigensolver.init_args(self.qubitOp, k=1)
        results = exact_eigensolver.run()
        self.reference_energy = results['energy']
        self.log.debug('The exact ground state energy is: {}'.format(results['energy']))

    @parameterized.expand([
        ['L_BFGS_B', 'local_statevector_simulator_py', 'matrix', 1],
        ['L_BFGS_B', 'local_statevector_simulator_py', 'paulis', 1],
        ['L_BFGS_B', 'local_statevector_simulator_cpp', 'matrix', 1],
        ['L_BFGS_B', 'local_statevector_simulator_cpp', 'paulis', 1],
        ['SPSA', 'local_qasm_simulator_py', 'paulis', 1024],
        ['SPSA', 'local_qasm_simulator_py', 'grouped_paulis', 1024],
        ['SPSA', 'local_qasm_simulator_cpp', 'paulis', 1024],
        ['SPSA', 'local_qasm_simulator_cpp', 'grouped_paulis', 1024]
    ])
    def test_end2end_H2(self, optimizer, backend, mode, shots):
        var_form = get_variational_form_instance(self.variational_form)
        var_form.init_args(self.qubitOp.num_qubits, 3, entangler_map = {0: [1]})
        vqe_algorithm = get_algorithm_instance(self.algorithm)
        opt = get_optimizer_instance(optimizer)
        if optimizer == 'L_BFGS_B':
            opt.set_options(factr=10, maxfun=10)
        elif optimizer == 'SPSA':
            opt.init_args(max_trials=50)
            opt.set_options(save_steps=25)
        vqe_algorithm.setup_quantum_backend(backend=backend, shots=shots)
        vqe_algorithm.init_args(self.qubitOp, mode, var_form, opt)
        # vqe_algorithm._opt_max_iters = 300
        results = vqe_algorithm.run()
        self.log.debug("Testing with following setting: ")
        self.log.debug("optimizer: {}, backend: {}, mode: {}".format(optimizer, backend, mode))
        self.log.debug(results['energy'])

if __name__ == '__main__':
    unittest.main()
