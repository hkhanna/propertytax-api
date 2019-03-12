from bottle import run, get, request, response
import re


@get("/ptax")
def ptax():
    """ Single endpoint to get annual property tax information for a particular address

    Request URL parameters:
        address (string, optional): Address of property. Optionally can be just a state.
        value (integer, required): Property value
    
    Response:
        200 (json):
            property_tax_amount (string): Calculated annual amount of property tax
            property_tax_effective_rate (float): Effective annual rate of property tax
            information (string): Brief description of calculation
        400 (json):
            error (string): Description of error
    """

    # Confirm value is a number that is between 1e3 and 1e12
    # In the future, make this handle dollar signs and commas and anything else MLS throws our way.
    value = request.query.value
    if not value:
        response.status = 400
        return {"error": "No value provided"}

    try:
        value = float(value)
    except ValueError:
        response.status = 400
        return {"error": "Bad value provided"}

    if value < 1e3 or value > 1e12:
        response.status = 400
        return {"error": "Value out of range"}

    # Parse address to get state
    # Simple, brittle regex parser here to be replaced with something more robust.
    address = request.query.address
    state = None
    m = re.search("[A-Z]{2}", address)
    if m:
        state = m.group(0)

    # Identify property tax calculation function to be called based on the state_map dict.
    if address and not state:
        # If no state is included in an address, that's a malformed address.
        response.status = 400
        return {"error": "Please include two-character state (e.g., CA) in address."}
    elif not address:
        # If no address passed, use national average.
        fn = default
    elif state not in state_map:
        # If address passed, but state does not exist, use national average but log warning
        # since the front-end should not be passing states that are outside Compass markets.
        fn = default
        # TODO: LOG WARNING HERE #
    else:
        # This is the normal branch.
        fn = state_map[state]

    # Call appropriate property tax function
    result = fn(address, value)

    return result


def california(address, value):
    """California Property Tax - Last Updated March, 2019
    - Calculation is a simple statewide average percentage times the value. 
    - As of the 2017 annual report, the statewide average is 1.143%.
    - Other reports of average effective rates (~0.74%) are misleading due to Proposition 13.
    - Property tax in all areas of California is at least 1%. 
    - Precise property tax rates is very difficult to calculate in a scalable way because of "tax rate area" polygons.
    - Tax rate areas can pass bonds to fund additional local services.
    - This may increase property tax beyond 1%, but it always stays pretty close to 1%.
    """

    property_tax_effective_rate = 0.01143
    property_tax_amount = f"{value * property_tax_effective_rate:.2f}"
    information = "Based on the California statewide average property tax rate"

    return {
        "property_tax_amount": property_tax_amount,
        "property_tax_effective_rate": property_tax_effective_rate,
        "information": information,
    }

def colorado(address, value):
    """Colorado Property Tax - Last Updated March, 2019
    - Calculation is a simple statewide average percentage times the value. 
    - As of 2018, the statewide average is 0.57%
    - CO has similar issues to CA where there are different tax rate areas.
    """

    property_tax_effective_rate = 0.0057
    property_tax_amount = f"{value * property_tax_effective_rate:.2f}"
    information = "Based on the Colorado statewide average property tax rate"

    return {
        "property_tax_amount": property_tax_amount,
        "property_tax_effective_rate": property_tax_effective_rate,
        "information": information,
    }


def washington_dc(amount, value):
    """Washington DC Property Tax - Last Updated March, 2019
    - Assumes buyer will be living there, so deduct the homestead exemption of $73,350
    - Then apply the standing property tax rate of 0.85%
    """

    assessed_value = max(value - 73350, 0)
    property_tax_amount = assessed_value * 0.0085
    property_tax_effective_rate = property_tax_amount / value

    property_tax_amount = f"{property_tax_amount:.2f}"
    property_tax_effective_rate = f"{property_tax_effective_rate:.5f}"
    information = (
        "Based on DC-wide property tax rate after application of homestead exemption"
    )

    return {
        "property_tax_amount": property_tax_amount,
        "property_tax_effective_rate": property_tax_effective_rate,
        "information": information,
    }


def default(address, value):
    """Default Property Tax Calculation -- Last Updated March, 2019
    - Calculation is a simple nationwide average percentage times the value.
    - As of April 3, 2018, the nationwide average is 1.17%. 
    - Understates the national average due to the way California is handled.
    - In CA, this number treats the effective rate is based on the FMV of the properties rather than the assessed value.
    """

    property_tax_effective_rate = 0.0117
    property_tax_amount = f"{value * property_tax_effective_rate:.2f}"
    information = "Based on the nationwide average property tax rate"

    return {
        "property_tax_amount": property_tax_amount,
        "property_tax_effective_rate": property_tax_effective_rate,
        "information": information,
    }


state_map = {"CA": california, "CO": colorado, "DC": washington_dc}
run(port=8080)
