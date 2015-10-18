import contextlib
import unittest
import unittest.mock

import aioxmpp.callbacks
import aioxmpp.structs

from aioxmpp.testutils import CoroutineMock, run_coroutine

import mlxc.client
import mlxc.config

import mlxcqt.client as client

from mlxcqt import Qt


class TestAccountsModel(unittest.TestCase):
    def test_init(self):
        base = unittest.mock.Mock()
        with contextlib.ExitStack() as stack:
            ModelListAdaptor = stack.enter_context(
                unittest.mock.patch(
                    "mlxcqt.model_adaptor.ModelListAdaptor",
                    new=base.ModelListAdaptor
                )
            )

            model = client.AccountsModel(base.accounts)

        self.assertSequenceEqual(
            base.mock_calls,
            [
                unittest.mock.call.ModelListAdaptor(
                    base.accounts._jidlist,
                    model
                ),
                unittest.mock.call.accounts.on_account_enabled.connect(
                    model._account_enabled
                ),
                unittest.mock.call.accounts.on_account_disabled.connect(
                    model._account_disabled
                ),
                unittest.mock.call.accounts.on_account_refresh.connect(
                    model._account_refresh
                )
            ]
        )

    def setUp(self):
        self.base = unittest.mock.Mock()
        self.base.accounts = unittest.mock.MagicMock()
        self.base.accounts.on_account_enabled = aioxmpp.callbacks.AdHocSignal()
        self.base.accounts.on_account_disabled = aioxmpp.callbacks.AdHocSignal()
        self.base.accounts.on_account_refresh = aioxmpp.callbacks.AdHocSignal()
        self.accounts = self.base.accounts
        self.model = client.AccountsModel(self.accounts)

    def test_rowCount_returns_accounts_length_for_invalid_model_index(self):
        self.assertEqual(
            self.model.rowCount(Qt.QModelIndex()),
            len(self.accounts)
        )

    def test_rowCount_returns_zero_for_valid_model_index(self):
        index = self.model.index(0, parent=Qt.QModelIndex())
        self.assertEqual(self.model.rowCount(index), 0)

    def test_data_returns_None_for_invalid_model_index(self):
        self.assertIsNone(
            self.model.data(Qt.QModelIndex(), object())
        )

    def test_data_returns_None_for_non_display_role(self):
        self.accounts.__len__.return_value = 1
        index = self.model.index(0, parent=Qt.QModelIndex())
        self.assertIsNone(
            self.model.data(index, Qt.Qt.ToolTipRole)
        )

    def test_data_returns_str_of_accounts_jid_for_display_role(self):
        self.accounts.__len__.return_value = 1
        index = self.model.index(0, parent=Qt.QModelIndex())
        self.assertEqual(
            self.model.data(index, Qt.Qt.DisplayRole),
            str(self.accounts[0].jid)
        )

    def test_data_returns_None_on_IndexError(self):
        self.accounts.__len__.return_value = 1
        self.accounts.__getitem__.side_effect = IndexError()
        index = self.model.index(0, parent=Qt.QModelIndex())
        self.assertIsNone(
            self.model.data(index, Qt.Qt.DisplayRole)
        )

    def test_headerData_returns_None_for_vertical_orientation(self):
        self.assertIsNone(
            self.model.headerData(0, Qt.Qt.Vertical, Qt.Qt.DisplayRole)
        )

    def test_headerData_returns_None_for_non_zero_section(self):
        self.assertIsNone(
            self.model.headerData(1, Qt.Qt.Horizontal, Qt.Qt.DisplayRole)
        )

    def test_headerData_returns_None_for_non_Display_role(self):
        self.assertIsNone(
            self.model.headerData(0, Qt.Qt.Horizontal, Qt.Qt.ToolTipRole)
        )

    def test_headerData_returns_JID_for_horizontal_section_0_display(self):
        self.assertEqual(
            "JID",
            self.model.headerData(0, Qt.Qt.Horizontal, Qt.Qt.DisplayRole)
        )

    def test_flags_returns_checkability(self):
        self.assertEqual(
            (Qt.Qt.ItemIsEnabled |
             Qt.Qt.ItemIsSelectable |
             Qt.Qt.ItemIsUserCheckable),
            self.model.flags(Qt.QModelIndex())
        )
        self.assertEqual(
            (Qt.Qt.ItemIsEnabled |
             Qt.Qt.ItemIsSelectable |
             Qt.Qt.ItemIsUserCheckable),
            self.model.flags(self.model.index(0, parent=Qt.QModelIndex()))
        )

    def test_data_returns_enabledness_for_check_state_role(self):
        self.accounts.__len__.return_value = 1
        self.accounts.__getitem__().enabled = True
        index = self.model.index(0, parent=Qt.QModelIndex())
        self.assertEqual(
            self.model.data(index, Qt.Qt.CheckStateRole),
            Qt.Qt.Checked,
        )
        self.accounts.__getitem__().enabled = False
        self.assertEqual(
            self.model.data(index, Qt.Qt.CheckStateRole),
            Qt.Qt.Unchecked
        )

    def test_setData_with_positive_check_state_enables_account(self):
        self.accounts.__len__.return_value = 1
        index = self.model.index(0, parent=Qt.QModelIndex())
        self.model.setData(index, Qt.Qt.Checked, Qt.Qt.CheckStateRole)
        self.assertIn(
            unittest.mock.call.set_account_enabled(
                self.accounts[0].jid,
                True),
            self.accounts.mock_calls
        )
        self.assertNotIn(
            unittest.mock.call.set_account_enabled(
                self.accounts[0].jid,
                False),
            self.accounts.mock_calls
        )

    def test_setData_with_negative_check_state_disables_account(self):
        self.accounts.__len__.return_value = 1
        index = self.model.index(0, parent=Qt.QModelIndex())
        self.model.setData(index, Qt.Qt.Unchecked, Qt.Qt.CheckStateRole)
        self.assertIn(
            unittest.mock.call.set_account_enabled(
                self.accounts[0].jid,
                False),
            self.accounts.mock_calls
        )
        self.assertNotIn(
            unittest.mock.call.set_account_enabled(
                self.accounts[0].jid,
                True),
            self.accounts.mock_calls
        )

    def test_call_dataChanged_when_account_gets_enabled(self):
        account = object()

        self.accounts.__len__.return_value = 1

        self.base.mock_calls.clear()

        with contextlib.ExitStack() as stack:
            dataChanged = stack.enter_context(unittest.mock.patch.object(
                self.model,
                "dataChanged",
                new=self.base.dataChanged
            ))
            index = stack.enter_context(unittest.mock.patch.object(
                self.model,
                "index",
                new=self.base.index_
            ))

            self.accounts.on_account_enabled(account)

        calls = list(self.base.mock_calls)
        self.assertSequenceEqual(
            calls,
            [
                unittest.mock.call.accounts.account_index(account),
                unittest.mock.call.index_(self.accounts.account_index(),
                                          column=0,
                                          parent=Qt.QModelIndex()),
                unittest.mock.call.dataChanged.emit(index(), index(),
                                                    [Qt.Qt.CheckStateRole])
            ]
        )

    def test_call_dataChanged_when_account_gets_disabled(self):
        account = object()

        self.accounts.__len__.return_value = 1

        self.base.mock_calls.clear()

        with contextlib.ExitStack() as stack:
            dataChanged = stack.enter_context(unittest.mock.patch.object(
                self.model,
                "dataChanged",
                new=self.base.dataChanged
            ))
            index = stack.enter_context(unittest.mock.patch.object(
                self.model,
                "index",
                new=self.base.index_
            ))

            self.accounts.on_account_disabled(account)

        calls = list(self.base.mock_calls)
        self.assertSequenceEqual(
            calls,
            [
                unittest.mock.call.accounts.account_index(account),
                unittest.mock.call.index_(self.accounts.account_index(),
                                          column=0,
                                          parent=Qt.QModelIndex()),
                unittest.mock.call.dataChanged.emit(index(), index(),
                                                    [Qt.Qt.CheckStateRole])
            ]
        )

    def test_call_dataChanged_when_account_gets_refreshed(self):
        account = object()

        self.accounts.__len__.return_value = 1

        self.base.mock_calls.clear()

        with contextlib.ExitStack() as stack:
            dataChanged = stack.enter_context(unittest.mock.patch.object(
                self.model,
                "dataChanged",
                new=self.base.dataChanged
            ))
            index = stack.enter_context(unittest.mock.patch.object(
                self.model,
                "index",
                new=self.base.index_
            ))

            self.accounts.on_account_refresh(account)

        calls = list(self.base.mock_calls)
        self.assertSequenceEqual(
            calls,
            [
                unittest.mock.call.accounts.account_index(account),
                unittest.mock.call.index_(self.accounts.account_index(),
                                          column=0,
                                          parent=Qt.QModelIndex()),
                unittest.mock.call.dataChanged.emit(index(), index())
            ]
        )


class TestAccountManager(unittest.TestCase):
    def test_is_mlxc_account_manager(self):
        self.assertTrue(issubclass(
            client.AccountManager,
            mlxc.client.AccountManager
        ))

    def setUp(self):
        self.manager = client.AccountManager()

    def test_qmodel_is_AccountsModel(self):
        self.assertIsInstance(
            self.manager.qmodel,
            client.AccountsModel
        )


class TestClient(unittest.TestCase):
    def test_is_mlxc_client(self):
        self.assertTrue(issubclass(
            client.Client,
            mlxc.client.Client
        ))

    def test_uses_mlxcqt_AccountManager(self):
        self.assertIs(client.Client.AccountManager,
                      client.AccountManager)

    def setUp(self):
        self.c = client.Client(mlxc.config.make_config_manager())

    def test__decide_on_certificate_prompts_user(self):
        account = object()
        verifier = object()
        accept = object()

        with contextlib.ExitStack() as stack:
            DlgCheckCertificate = stack.enter_context(unittest.mock.patch(
                "mlxcqt.check_certificate.DlgCheckCertificate"
            ))
            DlgCheckCertificate().run = CoroutineMock()
            DlgCheckCertificate().run.return_value = accept, False
            DlgCheckCertificate.mock_calls.clear()

            result = run_coroutine(
                self.c._decide_on_certificate(account, verifier)
            )

        self.assertSequenceEqual(
            DlgCheckCertificate.mock_calls,
            [
                unittest.mock.call(account, verifier),
                unittest.mock.call().run()
            ]
        )

        self.assertEqual(
            result,
            accept
        )

    def test__decide_on_certificate_pins_if_user_allows(self):
        base = unittest.mock.Mock()

        verifier = base.verifier
        account = base.account

        with contextlib.ExitStack() as stack:
            DlgCheckCertificate = stack.enter_context(unittest.mock.patch(
                "mlxcqt.check_certificate.DlgCheckCertificate",
                new=base.DlgCheckCertificate
            ))
            DlgCheckCertificate().run = CoroutineMock()
            DlgCheckCertificate().run.return_value = True, True

            pin_store = stack.enter_context(unittest.mock.patch.object(
                self.c,
                "pin_store",
                new=base.pin_store
            ))

            base.mock_calls.clear()

            result = run_coroutine(
                self.c._decide_on_certificate(account, verifier)
            )

        calls = list(base.mock_calls)
        self.assertSequenceEqual(
            calls,
            [
                unittest.mock.call.DlgCheckCertificate(account, verifier),
                unittest.mock.call.DlgCheckCertificate().run(),
                unittest.mock.call.pin_store.pin(
                    account.jid.domain,
                    verifier.leaf_x509
                )
            ]
        )

        self.assertTrue(result)

    def test__decide_on_certificate_does_not_pin_unaccepted(self):
        base = unittest.mock.Mock()

        verifier = base.verifier
        account = base.account

        with contextlib.ExitStack() as stack:
            DlgCheckCertificate = stack.enter_context(unittest.mock.patch(
                "mlxcqt.check_certificate.DlgCheckCertificate",
                new=base.DlgCheckCertificate
            ))
            DlgCheckCertificate().run = CoroutineMock()
            DlgCheckCertificate().run.return_value = False, True

            pin_store = stack.enter_context(unittest.mock.patch.object(
                self.c,
                "pin_store",
                new=base.pin_store
            ))

            base.mock_calls.clear()

            result = run_coroutine(
                self.c._decide_on_certificate(account, verifier)
            )

        calls = list(base.mock_calls)
        self.assertSequenceEqual(
            calls,
            [
                unittest.mock.call.DlgCheckCertificate(account, verifier),
                unittest.mock.call.DlgCheckCertificate().run(),
            ]
        )

        self.assertFalse(result)



# foo