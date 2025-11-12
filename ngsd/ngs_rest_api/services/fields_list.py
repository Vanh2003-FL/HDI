fields_ticket = {
    'channel': 'x_channel_type',
    # 'queryReason': 'x_tracing_type',
    'fundTransfer': 'x_ft_code',
    'transDate': 'x_date',
    'transAmount': 'x_ft_amount',
    'currency': 'currency_id',
    'transMessage': 'x_transaction_note',
    'callTranscript': 'description',
    'chatContent': 'description',
    'transCode': 'x_so_gd',
}

fields_partner = {
    'cif': 'vat',
    'clientName': 'name',
    'identityNo': 'x_identify',
    'phoneNo': 'santi_phone',
    'birthDay': 'x_dob',
    'gender': 'title.name',
    'address': 'contact_address',
    'email': 'email',
}

fields_card = {
    'cif': 'vat',
    'cardId': 'name',
    'cardType': 'x_identify',
    'limitAmount': 'phone',
}
