// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DataConsent {

    struct ConsentEntry {
        string purpose_id;
        bool consent_status;
        uint256 purpose_retention;
        uint256 purpose_expiry;
    }

    struct ConsentScope {
        string dataElement;
        ConsentEntry[] consents;  // Array of consent entries
    }

    struct Consent {
        string dp_id;
        string df_id;
        string cp_id;
        ConsentScope[] consent_scope;  // Array of consent scopes
    }

    mapping(address => Consent) public userConsents;

    // Event to log consent storage
    event ConsentStored(
        address indexed user,
        string dp_id,
        string df_id,
        string cp_id
    );

    // Function to store the consent
    function storeConsent(
        string memory _dp_id,
        string memory _df_id,
        string memory _cp_id,
        string[] memory _dataElements,
        string[][] memory _purpose_ids,
        bool[][] memory _consent_statuses,
        uint256[][] memory _purpose_retention,
        uint256[][] memory _purpose_expiry
    ) public {

        Consent storage consent = userConsents[msg.sender];
        consent.dp_id = _dp_id;
        consent.df_id = _df_id;
        consent.cp_id = _cp_id;

        for (uint256 i = 0; i < _dataElements.length; i++) {
            ConsentScope storage newScope = consent.consent_scope.push();
            newScope.dataElement = _dataElements[i];
            
            uint256 numConsents = _consent_statuses[i].length;  // Use length of consent_statuses array
            for (uint256 j = 0; j < numConsents; j++) {
                ConsentEntry memory newConsentEntry;
                newConsentEntry.purpose_id = _purpose_ids[i][j];
                newConsentEntry.consent_status = _consent_statuses[i][j];
                newConsentEntry.purpose_retention = _purpose_retention[i][j];
                newConsentEntry.purpose_expiry = _purpose_expiry[i][j];

                newScope.consents.push(newConsentEntry);
            }
        }

        emit ConsentStored(msg.sender, _dp_id, _df_id, _cp_id);
    }

    // Function to get user consent
    function getConsent(address _user) public view returns (Consent memory) {
        return userConsents[_user];
    }
}