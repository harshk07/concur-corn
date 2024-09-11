// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SaveConsent {
    
    // Struct to store consent details
    struct ConsentDetail {
        string[] purpose_ids;
        bool[] consentGiven;
        uint256[] expireDate;
        uint256[] retentionPeriod;
    }

    // Struct to store customer info
    struct CustomerInfo {
        string dp_id;
    }

    // Struct to store consent information for a specific data element
    struct ConsentInfo {
        string data_element;
        string[] purpose_ids;
        bool[] consentGiven;
        uint256[] expireDate;
        uint256[] retentionPeriod;
    }

    // Mapping to store customer information by their address
    mapping(address => CustomerInfo) private customerInfos;

    // Mapping to store consents by customer's address and data element
    mapping(address => mapping(string => ConsentDetail)) private consents;

    // Mapping to store data element keys associated with a customer
    mapping(address => string[]) private dataElementKeys;

    // Mapping to associate a dp_id with a customer address
    mapping(string => address) private dpIdToAddress;

    // Register customer information and manage consents
    function registerAndManageConsent(
        string memory dp_id,
        string memory data_element,
        string[] memory purpose_ids,
        bool[] memory consentGiven,
        uint256[] memory expireDate,
        uint256[] memory retentionPeriod
    ) public {
        address customerAddress = msg.sender;

        // Ensure the dp_id is not registered to another wallet address
        require(
            dpIdToAddress[dp_id] == address(0) || 
            dpIdToAddress[dp_id] == customerAddress,
            "dp_id is already registered with another wallet address"
        );

        // Register customer information
        customerInfos[customerAddress] = CustomerInfo(dp_id);

        // Link dp_id with the customer's wallet address
        dpIdToAddress[dp_id] = customerAddress;

        // Save consent details for the customer and data element
        consents[customerAddress][data_element] = ConsentDetail({
            purpose_ids: purpose_ids,
            consentGiven: consentGiven,
            expireDate: expireDate,
            retentionPeriod: retentionPeriod
        });

        // Track data element key if not already present
        if (!keyExists(customerAddress, data_element)) {
            dataElementKeys[customerAddress].push(data_element);
        }
    }

    // Check if a data element key already exists for a customer
    function keyExists(
        address customerAddress, 
        string memory data_element
    ) private view returns (bool) {
        string[] memory keys = dataElementKeys[customerAddress];
        for (uint i = 0; i < keys.length; i++) {
            if (keccak256(bytes(keys[i])) == keccak256(bytes(data_element))) {
                return true;
            }
        }
        return false;
    }

    // Retrieve all consents for a specific customer
    function getConsents(
        address customerAddress
    ) public view returns (ConsentInfo[] memory) {
        string[] memory keys = dataElementKeys[customerAddress];
        uint256 numConsents = keys.length;

        // Create array to hold consent information
        ConsentInfo[] memory consentInfos = new ConsentInfo[](numConsents);

        // Populate consent information
        for (uint i = 0; i < numConsents; i++) {
            ConsentDetail storage consentDetail = consents[customerAddress][keys[i]];
            consentInfos[i] = ConsentInfo({
                data_element: keys[i],
                purpose_ids: consentDetail.purpose_ids,
                consentGiven: consentDetail.consentGiven,
                expireDate: consentDetail.expireDate,
                retentionPeriod: consentDetail.retentionPeriod
            });
        }

        return consentInfos;
    }

    // Retrieve the total number of consents for a customer
    function getConsentCount(
        address customerAddress
    ) public view returns (uint256) {
        return dataElementKeys[customerAddress].length;
    }

    // Retrieve a specific consent by index for a customer
    function getConsentByIndex(
        address customerAddress, 
        uint256 index
    ) public view returns (ConsentInfo memory) {
        require(index < dataElementKeys[customerAddress].length, "Index out of bounds");

        string memory dataElement = dataElementKeys[customerAddress][index];
        ConsentDetail storage consentDetail = consents[customerAddress][dataElement];

        return ConsentInfo({
            data_element: dataElement,
            purpose_ids: consentDetail.purpose_ids,
            consentGiven: consentDetail.consentGiven,
            expireDate: consentDetail.expireDate,
            retentionPeriod: consentDetail.retentionPeriod
        });
    }

    // Retrieve customer information (dp_id) by customer address
    function getCustomerInfo(
        address customerAddress
    ) public view returns (string memory) {
        return customerInfos[customerAddress].dp_id;
    }
}